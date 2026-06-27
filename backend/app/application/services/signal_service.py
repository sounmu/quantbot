from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.entities import HoldingChange, SignalDaily, SignalParticipant
from app.domain.repositories import (
    HoldingChangeRepository,
    SecurityPriceRepository,
    SignalDailyRepository,
)
from app.domain.value_objects import ChangeType, holding_key


@dataclass(slots=True)
class SignalWithParticipants:
    signal: SignalDaily
    participants: list[SignalParticipant]


class SignalService:
    def __init__(
        self,
        *,
        changes: HoldingChangeRepository,
        security_prices: SecurityPriceRepository,
        signals: SignalDailyRepository,
    ) -> None:
        self._changes = changes
        self._security_prices = security_prices
        self._signals = signals

    async def recompute_daily(self, *, as_of_date: date | None = None) -> int:
        changes = await self._changes.signal_sources(as_of_date=as_of_date)
        dates = sorted({change.as_of_date for change in changes})
        if as_of_date is not None and as_of_date not in dates:
            dates = [as_of_date]
        if not dates:
            return 0

        signals: list[SignalDaily] = []
        for target_date in dates:
            daily_changes = [change for change in changes if change.as_of_date == target_date]
            keys = [
                key
                for change in daily_changes
                if (key := holding_key(change.holding_ticker, change.holding_name, change.security_id))
            ]
            prices = await self._security_prices.latest_adj_close_by_security(
                keys,
                on_or_before=target_date,
            )
            signals.extend(aggregate_daily_signals(daily_changes, prices))

        return await self._signals.replace_for_dates(dates, signals)

    async def daily(
        self,
        *,
        as_of_date: date | None = None,
        limit: int = 100,
    ) -> list[SignalDaily]:
        return await self._signals.daily(as_of_date=as_of_date, limit=limit)

    async def for_security(
        self,
        security_key: str,
        *,
        limit: int = 100,
    ) -> list[SignalWithParticipants]:
        history = await self._signals.for_security(security_key, limit=limit)
        result: list[SignalWithParticipants] = []
        for signal in history:
            participants = await self._changes.signal_participants(
                signal.security_key,
                as_of_date=signal.as_of_date,
            )
            result.append(SignalWithParticipants(signal=signal, participants=participants))
        return result


def aggregate_daily_signals(
    changes: list[HoldingChange],
    adj_close_by_security: dict[str, float],
) -> list[SignalDaily]:
    buckets: dict[str, _SignalBucket] = {}
    for change in changes:
        key = holding_key(change.holding_ticker, change.holding_name, change.security_id)
        if key is None:
            continue

        direction = _signal_direction(change.change_type)
        if direction is None:
            continue

        bucket = buckets.get(key)
        if bucket is None:
            bucket = _SignalBucket(
                security_key=key,
                as_of_date=change.as_of_date,
                security_ticker=change.holding_ticker or key,
                security_name=change.holding_name,
            )
            buckets[key] = bucket

        if direction == "BUY":
            bucket.n_buying += 1
        else:
            bucket.n_selling += 1

        if change.shares_delta is not None:
            bucket.net_shares_flow += change.shares_delta
            bucket.has_shares_flow = True
            if key in adj_close_by_security:
                bucket.net_dollar_flow += change.shares_delta * adj_close_by_security[key]
                bucket.has_dollar_flow = True

    return [
        bucket.to_signal()
        for bucket in sorted(
            buckets.values(),
            key=lambda item: (-item.conviction_score, item.security_key),
        )
    ]


@dataclass(slots=True)
class _SignalBucket:
    security_key: str
    as_of_date: date
    security_ticker: str
    security_name: str
    n_buying: int = 0
    n_selling: int = 0
    net_shares_flow: float = 0
    net_dollar_flow: float = 0
    has_shares_flow: bool = False
    has_dollar_flow: bool = False

    @property
    def conviction_score(self) -> float:
        return float(self.n_buying - self.n_selling)

    def to_signal(self) -> SignalDaily:
        return SignalDaily(
            security_key=self.security_key,
            as_of_date=self.as_of_date,
            security_ticker=self.security_ticker,
            security_name=self.security_name,
            n_buying=self.n_buying,
            n_selling=self.n_selling,
            net_shares_flow=self.net_shares_flow if self.has_shares_flow else None,
            net_dollar_flow=self.net_dollar_flow if self.has_dollar_flow else None,
            conviction_score=self.conviction_score,
        )


def _signal_direction(change_type: str) -> str | None:
    if change_type in {ChangeType.NEW, ChangeType.INCREASE}:
        return "BUY"
    if change_type in {ChangeType.EXIT, ChangeType.DECREASE}:
        return "SELL"
    return None
