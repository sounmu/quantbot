from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.services.etf_service import EtfService, EtfWithMetric
from app.application.services.flow_service import FlowService
from app.application.services.signal_service import SignalService
from app.domain.entities import EtfFlowDaily, HoldingChange
from app.domain.value_objects import holding_key
from app.interfaces.deps import get_etf_service, get_flow_service, get_signal_service
from app.interfaces.schemas.change import HoldingChangeResponse, PositionHistoryPointResponse
from app.interfaces.schemas.etf import (
    CompareItem,
    CompareResponse,
    EtfDetailResponse,
    EtfListItem,
    EtfListResponse,
)
from app.interfaces.schemas.flow import EtfFlowResponse
from app.interfaces.schemas.holding import HoldingResponse
from app.interfaces.schemas.price import PricePointResponse

router = APIRouter(prefix="/api/etfs", tags=["etfs"])


@router.get("", response_model=EtfListResponse)
async def list_etfs(
    q: str | None = None,
    issuer: str | None = None,
    theme: str | None = None,
    sort: str = Query(default="name", pattern="^(expense_ratio|return_1y|return_ytd|name)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: EtfService = Depends(get_etf_service),
) -> EtfListResponse:
    items, total = await service.list_etfs(
        q=q,
        issuer=issuer,
        theme=theme,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    return EtfListResponse(
        items=[_to_list_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/compare", response_model=CompareResponse)
async def compare_etfs(
    tickers: str,
    range_: str = Query(default="1y", alias="range", pattern="^(1m|3m|6m|1y|ytd|max)$"),
    service: EtfService = Depends(get_etf_service),
) -> CompareResponse:
    ticker_list = sorted(
        {ticker.strip().upper() for ticker in tickers.split(",") if ticker.strip()}
    )
    if len(ticker_list) > 10:
        raise HTTPException(status_code=422, detail="A maximum of 10 tickers can be compared")
    result = await service.compare(ticker_list, range_=range_)
    return CompareResponse(
        items=[_to_compare_item(item) for item in result.items],
        series=result.series,
    )


@router.get("/{ticker}", response_model=EtfDetailResponse)
async def get_etf_detail(
    ticker: str,
    service: EtfService = Depends(get_etf_service),
) -> EtfDetailResponse:
    detail = await service.get_detail(ticker)
    if detail is None:
        raise HTTPException(status_code=404, detail="ETF not found")
    return _to_detail_item(detail)


@router.get("/{ticker}/prices", response_model=list[PricePointResponse])
async def get_prices(
    ticker: str,
    range_: str = Query(default="1y", alias="range", pattern="^(1m|3m|6m|1y|ytd|max)$"),
    service: EtfService = Depends(get_etf_service),
) -> list[PricePointResponse]:
    await _require_etf(ticker, service)
    prices = await service.get_prices(ticker, range_=range_)
    return [
        PricePointResponse(
            date=point.on,
            open=point.open,
            high=point.high,
            low=point.low,
            close=point.close,
            nav=point.nav,
            volume=point.volume,
        )
        for point in prices
    ]


@router.get("/{ticker}/flow", response_model=list[EtfFlowResponse])
async def get_flow(
    ticker: str,
    range_: str = Query(default="1y", alias="range", pattern="^(1m|3m|6m|1y|ytd|max)$"),
    service: EtfService = Depends(get_etf_service),
    flow_service: FlowService = Depends(get_flow_service),
) -> list[EtfFlowResponse]:
    await _require_etf(ticker, service)
    flows = await flow_service.series(ticker, range_=range_)
    return [_to_flow_response(flow) for flow in flows]


@router.get("/{ticker}/holdings", response_model=list[HoldingResponse])
async def get_holdings(
    ticker: str,
    as_of_date: date | None = Query(default=None, alias="date"),
    service: EtfService = Depends(get_etf_service),
    signal_service: SignalService = Depends(get_signal_service),
    flow_service: FlowService = Depends(get_flow_service),
) -> list[HoldingResponse]:
    await _require_etf(ticker, service)
    holdings = await service.get_holdings(ticker, as_of_date=as_of_date)
    snapshot_date = holdings[0].as_of_date if holdings else as_of_date
    changes = await service.get_holding_changes(
        ticker,
        as_of_date=snapshot_date if as_of_date is None else as_of_date,
        include_unchanged=True,
    )
    changes_by_key = {
        key: change
        for change in changes
        if (key := holding_key(change.holding_ticker, change.holding_name, change.security_id))
    }
    holding_keys = [
        key
        for holding in holdings
        if (key := holding_key(holding.holding_ticker, holding.holding_name, holding.security_id))
    ]
    cross_signals = (
        await signal_service.cross_signals(holding_keys, as_of_date=snapshot_date)
        if holding_keys and snapshot_date is not None
        else {}
    )
    _, flow_components = (
        await flow_service.components(ticker, as_of_date=snapshot_date)
        if snapshot_date is not None
        else (None, [])
    )
    flow_components_by_key = {component.holding_key: component for component in flow_components}
    return [
        HoldingResponse(
            as_of_date=holding.as_of_date,
            holding_key=key,
            holding_ticker=holding.holding_ticker,
            security_id=holding.security_id,
            holding_name=holding.holding_name,
            weight=holding.weight,
            shares=holding.shares,
            market_value=holding.market_value,
            change_type=change.change_type if change else None,
            shares_delta=change.shares_delta if change else None,
            shares_delta_pct=change.shares_delta_pct if change else None,
            weight_delta=change.weight_delta if change else None,
            signal_n_buying=signal.n_buying if signal else None,
            signal_n_selling=signal.n_selling if signal else None,
            signal_conviction=signal.conviction_score if signal else None,
            flow_adjusted=flow_component.flow_adjusted if flow_component else None,
            active_direction=flow_component.active_direction if flow_component else None,
            active_intensity=flow_component.active_intensity if flow_component else None,
            active_confidence=flow_component.active_confidence if flow_component else None,
            active_residual=flow_component.active_residual if flow_component else None,
            passive_shares=flow_component.passive_shares if flow_component else None,
            residual_nav_bp=flow_component.residual_nav_bp if flow_component else None,
            residual_position_pct=flow_component.residual_position_pct if flow_component else None,
        )
        for holding in holdings
        for key in [
            holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
        ]
        if key is not None
        for change in [changes_by_key.get(key)]
        for signal in [cross_signals.get(key)]
        for flow_component in [flow_components_by_key.get(key)]
    ]


@router.get("/{ticker}/holdings/dates", response_model=list[date])
async def get_holding_dates(
    ticker: str,
    service: EtfService = Depends(get_etf_service),
) -> list[date]:
    await _require_etf(ticker, service)
    return await service.get_holding_dates(ticker)


@router.get("/{ticker}/changes", response_model=list[HoldingChangeResponse])
async def get_holding_changes(
    ticker: str,
    as_of_date: date | None = Query(default=None, alias="date"),
    include_unchanged: bool = False,
    service: EtfService = Depends(get_etf_service),
) -> list[HoldingChangeResponse]:
    await _require_etf(ticker, service)
    changes = await service.get_holding_changes(
        ticker,
        as_of_date=as_of_date,
        include_unchanged=include_unchanged,
    )
    return [_to_change_response(change) for change in changes]


@router.get(
    "/{ticker}/positions/{holding}/history", response_model=list[PositionHistoryPointResponse]
)
async def get_position_history(
    ticker: str,
    holding: str,
    service: EtfService = Depends(get_etf_service),
) -> list[PositionHistoryPointResponse]:
    await _require_etf(ticker, service)
    history = await service.get_position_history(ticker, holding)
    return [
        PositionHistoryPointResponse(
            as_of_date=point.as_of_date,
            holding_ticker=point.holding_ticker,
            holding_name=point.holding_name,
            shares=point.shares,
            weight=point.weight,
            market_value=point.market_value,
        )
        for point in history
    ]


def _to_list_item(item: EtfWithMetric) -> EtfListItem:
    return EtfListItem(
        ticker=item.etf.ticker,
        name=item.etf.name,
        issuer=item.etf.issuer,
        theme=item.etf.theme,
        expense_ratio=item.etf.expense_ratio,
        exchange=item.etf.exchange,
        aum=_item_aum(item),
        in_signal_universe=item.etf.in_signal_universe,
        signal_universe_reason=item.etf.signal_universe_reason,
        discloses_daily=item.etf.discloses_daily,
        return_1m=item.metric.return_1m if item.metric else None,
        return_3m=item.metric.return_3m if item.metric else None,
        return_ytd=item.metric.return_ytd if item.metric else None,
        return_1y=item.metric.return_1y if item.metric else None,
    )


def _item_aum(item: EtfWithMetric) -> float | None:
    if item.etf.aum is not None:
        return item.etf.aum
    return item.metric.aum if item.metric else None


def _to_detail_item(item: EtfWithMetric) -> EtfDetailResponse:
    list_item = _to_list_item(item)
    return EtfDetailResponse(
        **list_item.model_dump(),
        inception_date=item.etf.inception_date,
        currency=item.etf.currency,
        description=item.etf.description,
        as_of=item.metric.as_of if item.metric else None,
    )


def _to_compare_item(item: EtfWithMetric) -> CompareItem:
    list_item = _to_list_item(item)
    return CompareItem(
        **list_item.model_dump(),
        as_of=item.metric.as_of if item.metric else None,
    )


def _to_change_response(change: HoldingChange) -> HoldingChangeResponse:
    return HoldingChangeResponse(
        ticker=change.ticker,
        as_of_date=change.as_of_date,
        prev_date=change.prev_date,
        holding_ticker=change.holding_ticker,
        holding_name=change.holding_name,
        change_type=change.change_type,
        shares_before=change.shares_before,
        shares_after=change.shares_after,
        shares_delta=change.shares_delta,
        shares_delta_pct=change.shares_delta_pct,
        weight_before=change.weight_before,
        weight_after=change.weight_after,
        weight_delta=change.weight_delta,
    )


def _to_flow_response(flow: EtfFlowDaily) -> EtfFlowResponse:
    return EtfFlowResponse(
        ticker=flow.ticker,
        as_of_date=flow.as_of_date,
        prev_date=flow.prev_date,
        net_flow=flow.net_flow,
        flow_rate=flow.flow_rate,
        active_buy=flow.active_buy,
        active_sell=flow.active_sell,
        turnover=flow.turnover,
        creation_r2=flow.creation_r2,
    )


async def _require_etf(ticker: str, service: EtfService) -> None:
    if await service.get_detail(ticker) is None:
        raise HTTPException(status_code=404, detail="ETF not found")
