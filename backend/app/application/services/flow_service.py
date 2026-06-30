from __future__ import annotations

from datetime import date

from app.domain.entities import EtfFlowDaily, Holding, SecurityFlowComponent
from app.domain.repositories import EtfFlowRepository, HoldingRepository
from app.domain.value_objects import holding_key


class FlowAdjusted:
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class ActiveDirection:
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"


class ActiveIntensity:
    NONE = "NONE"
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"


class ActiveConfidence:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


_RESIDUAL_NAV_WEAK_BP = 1.0
_RESIDUAL_NAV_MEDIUM_BP = 5.0
_RESIDUAL_NAV_STRONG_BP = 25.0
_RESIDUAL_POSITION_MEDIUM = 0.02
_RESIDUAL_POSITION_STRONG = 0.10
_POSITION_ONLY_NAV_FLOOR_BP = 0.25


class FlowService:
    def __init__(
        self,
        *,
        holdings: HoldingRepository,
        flows: EtfFlowRepository,
        shares_epsilon: float = 1.0,
    ) -> None:
        self._holdings = holdings
        self._flows = flows
        self._shares_epsilon = shares_epsilon

    async def recompute_for_etf(self, ticker: str, *, as_of_date: date | None = None) -> int:
        target_dates = [as_of_date] if as_of_date is not None else await self._holdings.snapshot_dates(ticker)
        written = 0
        for target_date in sorted(date_ for date_ in target_dates if date_ is not None):
            prev_date = await self._holdings.previous_snapshot_date(ticker, target_date)
            if prev_date is None:
                continue
            prev = await self._holdings.snapshot(ticker, prev_date)
            cur = await self._holdings.snapshot(ticker, target_date)
            flow, _ = decompose_flow(
                prev,
                cur,
                as_of_date=target_date,
                prev_date=prev_date,
                ticker=ticker,
                shares_epsilon=self._shares_epsilon,
            )
            if flow is None:
                continue
            written += await self._flows.replace_for_etf_date(flow)
        return written

    async def series(self, ticker: str, *, range_: str = "1y") -> list[EtfFlowDaily]:
        return await self._flows.series(ticker, range_=range_)

    async def latest(self, ticker: str) -> EtfFlowDaily | None:
        return await self._flows.latest(ticker)

    async def components(
        self,
        ticker: str,
        *,
        as_of_date: date | None = None,
    ) -> tuple[EtfFlowDaily | None, list[SecurityFlowComponent]]:
        target_date = as_of_date or await self._holdings.latest_snapshot_date(ticker)
        if target_date is None:
            return None, []
        prev_date = await self._holdings.previous_snapshot_date(ticker, target_date)
        if prev_date is None:
            return None, []

        prev = await self._holdings.snapshot(ticker, prev_date)
        cur = await self._holdings.snapshot(ticker, target_date)
        return decompose_flow(
            prev,
            cur,
            as_of_date=target_date,
            prev_date=prev_date,
            ticker=ticker,
            shares_epsilon=self._shares_epsilon,
        )


def decompose_flow(
    prev: list[Holding],
    cur: list[Holding],
    *,
    as_of_date: date,
    prev_date: date,
    ticker: str,
    shares_epsilon: float = 1.0,
) -> tuple[EtfFlowDaily | None, list[SecurityFlowComponent]]:
    """Estimate ETF-level fund flow and shares-level active residuals.

    The decomposition stays strictly in share-count space for classification.
    Dollars are used only to estimate the common creation/redemption rate and
    aggregate summary values.
    """
    prev_by_key = _holdings_by_key(prev)
    cur_by_key = _holdings_by_key(cur)
    if not prev_by_key or not cur_by_key:
        return None, []

    nav = sum(_positive_or_zero(holding.market_value) for holding in cur_by_key.values())
    if nav <= 0:
        return None, []

    price_by_key = {
        key: price
        for key, holding in cur_by_key.items()
        if (price := _current_price(holding)) is not None
    }
    common_keys = sorted(prev_by_key.keys() & cur_by_key.keys())
    denominator = 0.0
    common_net_flow = 0.0
    common_turnover = 0.0
    ss_total = 0.0

    for key in common_keys:
        current = cur_by_key[key]
        previous = prev_by_key[key]
        price = price_by_key.get(key)
        if price is None or previous.shares is None or current.shares is None:
            continue
        if previous.shares <= 0:
            continue

        delta_shares = current.shares - previous.shares
        previous_value_at_current_price = price * previous.shares
        delta_value = price * delta_shares
        denominator += previous_value_at_current_price
        common_net_flow += delta_value
        common_turnover += abs(delta_value)
        ss_total += delta_value**2

    if denominator <= 0:
        return None, []

    new_value = sum(
        _positive_or_zero(holding.market_value)
        for key, holding in cur_by_key.items()
        if key not in prev_by_key
    )
    exit_value = sum(
        _positive_or_zero(holding.market_value)
        for key, holding in prev_by_key.items()
        if key not in cur_by_key
    )
    net_flow = common_net_flow + new_value - exit_value
    flow_rate = net_flow / denominator

    components: list[SecurityFlowComponent] = []
    active_buy = 0.0
    active_sell = 0.0
    turnover_dollars = common_turnover + new_value + exit_value
    ss_residual = 0.0

    for key in sorted(prev_by_key.keys() | cur_by_key.keys()):
        previous = prev_by_key.get(key)
        current = cur_by_key.get(key)
        component = _component(
            key,
            previous,
            current,
            flow_rate=flow_rate,
            shares_epsilon=shares_epsilon,
            nav=nav,
        )
        if component is None:
            continue
        components.append(component)

        price = price_by_key.get(key)
        if price is not None:
            residual_value = price * component.active_residual
        elif current is None and previous is not None:
            residual_value = -_positive_or_zero(previous.market_value)
        else:
            residual_value = 0.0

        if component.active_residual > 0:
            active_buy += max(residual_value, 0.0)
        elif component.active_residual < 0:
            active_sell += abs(min(residual_value, 0.0))

        if key in prev_by_key and key in cur_by_key and price is not None:
            ss_residual += residual_value**2

    creation_r2 = None if ss_total == 0 else 1 - (ss_residual / ss_total)
    confidence = _active_confidence(creation_r2)
    for component in components:
        component.active_confidence = confidence

    flow = EtfFlowDaily(
        ticker=ticker.upper(),
        as_of_date=as_of_date,
        prev_date=prev_date,
        net_flow=net_flow,
        flow_rate=flow_rate,
        active_buy=active_buy,
        active_sell=active_sell,
        turnover=turnover_dollars / nav,
        creation_r2=creation_r2,
    )
    return flow, components


def _holdings_by_key(holdings: list[Holding]) -> dict[str, Holding]:
    result: dict[str, Holding] = {}
    for holding in holdings:
        key = holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
        if key is None or _is_zero_economic(holding):
            continue
        if key in result:
            raise ValueError(f"Duplicate holding key in snapshot: {key}")
        result[key] = holding
    return result


def _component(
    key: str,
    previous: Holding | None,
    current: Holding | None,
    *,
    flow_rate: float,
    shares_epsilon: float,
    nav: float,
) -> SecurityFlowComponent | None:
    source = current or previous
    if source is None:
        return None
    previous_shares = previous.shares if previous else None
    current_shares = current.shares if current else None
    if previous_shares is None and current_shares is None:
        return None

    before = previous_shares or 0.0
    after = current_shares or 0.0
    delta_shares = after - before
    passive_shares = flow_rate * before if previous is not None and current is not None else 0.0
    active_residual = delta_shares - passive_shares
    price = _current_price(current) if current is not None else _current_price(previous)
    residual_nav_bp = _residual_nav_bp(active_residual, price=price, nav=nav)
    residual_position_pct = _residual_position_pct(
        active_residual,
        before=before,
        after=after,
    )
    new_or_exit = previous is None or current is None
    active_direction, active_intensity, flow_adjusted = _classify_active_signal(
        active_residual,
        residual_nav_bp=residual_nav_bp,
        residual_position_pct=residual_position_pct,
        new_or_exit=new_or_exit,
        shares_epsilon=shares_epsilon,
    )

    return SecurityFlowComponent(
        holding_key=key,
        holding_ticker=source.holding_ticker,
        delta_shares=delta_shares,
        passive_shares=passive_shares,
        active_residual=active_residual,
        flow_adjusted=flow_adjusted,
        active_direction=active_direction,
        active_intensity=active_intensity,
        active_confidence=ActiveConfidence.LOW,
        residual_nav_bp=residual_nav_bp,
        residual_position_pct=residual_position_pct,
    )


def _current_price(holding: Holding) -> float | None:
    if holding.shares is None or holding.market_value is None:
        return None
    if holding.shares <= 0 or holding.market_value <= 0:
        return None
    return holding.market_value / holding.shares


def _positive_or_zero(value: float | None) -> float:
    if value is None or value <= 0:
        return 0.0
    return value


def _is_zero_economic(holding: Holding) -> bool:
    return (holding.shares or 0) == 0 and (holding.market_value or 0) == 0 and holding.weight == 0


def _residual_nav_bp(active_residual: float, *, price: float | None, nav: float) -> float | None:
    if price is None or nav <= 0:
        return None
    return (abs(active_residual) * price / nav) * 10_000


def _residual_position_pct(active_residual: float, *, before: float, after: float) -> float:
    base = max(abs(before), abs(after), 1.0)
    return abs(active_residual) / base


def _classify_active_signal(
    active_residual: float,
    *,
    residual_nav_bp: float | None,
    residual_position_pct: float,
    new_or_exit: bool,
    shares_epsilon: float,
) -> tuple[str, str, str]:
    if active_residual > 0:
        raw_direction = ActiveDirection.BUY
    elif active_residual < 0:
        raw_direction = ActiveDirection.SELL
    else:
        raw_direction = ActiveDirection.NEUTRAL

    nav_bp = residual_nav_bp or 0.0
    below_share_noise = abs(active_residual) <= shares_epsilon
    if raw_direction == ActiveDirection.NEUTRAL or (
        below_share_noise and nav_bp < _RESIDUAL_NAV_WEAK_BP
    ):
        return ActiveDirection.NEUTRAL, ActiveIntensity.NONE, FlowAdjusted.HOLD

    if new_or_exit:
        if nav_bp >= _RESIDUAL_NAV_STRONG_BP:
            intensity = ActiveIntensity.STRONG
        elif nav_bp >= _RESIDUAL_NAV_MEDIUM_BP:
            intensity = ActiveIntensity.MEDIUM
        else:
            intensity = ActiveIntensity.WEAK
    elif nav_bp >= _RESIDUAL_NAV_STRONG_BP:
        intensity = ActiveIntensity.STRONG
    elif nav_bp >= _RESIDUAL_NAV_MEDIUM_BP or (
        nav_bp >= _RESIDUAL_NAV_WEAK_BP
        and residual_position_pct >= _RESIDUAL_POSITION_STRONG
    ):
        intensity = ActiveIntensity.MEDIUM
    elif nav_bp >= _RESIDUAL_NAV_WEAK_BP or (
        nav_bp >= _POSITION_ONLY_NAV_FLOOR_BP
        and residual_position_pct >= _RESIDUAL_POSITION_MEDIUM
    ):
        intensity = ActiveIntensity.WEAK
    else:
        intensity = ActiveIntensity.NONE

    if intensity == ActiveIntensity.NONE:
        return ActiveDirection.NEUTRAL, intensity, FlowAdjusted.HOLD
    if raw_direction == ActiveDirection.BUY:
        return raw_direction, intensity, FlowAdjusted.BUY
    return raw_direction, intensity, FlowAdjusted.SELL


def _active_confidence(creation_r2: float | None) -> str:
    if creation_r2 is None:
        return ActiveConfidence.LOW
    if creation_r2 >= 0.75:
        return ActiveConfidence.HIGH
    if creation_r2 >= 0.25:
        return ActiveConfidence.MEDIUM
    return ActiveConfidence.LOW
