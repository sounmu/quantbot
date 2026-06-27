from __future__ import annotations

from app.domain.entities import (
    CollectionItemLog,
    CollectionRun,
    Etf,
    Holding,
    HoldingChange,
    Metric,
    PricePoint,
)
from app.infrastructure.db.orm_models import (
    CollectionItemLogORM,
    CollectionRunORM,
    EtfHoldingChangeORM,
    EtfHoldingORM,
    EtfMetricORM,
    EtfORM,
    EtfPriceORM,
)


def to_etf(row: EtfORM) -> Etf:
    return Etf(
        ticker=row.ticker,
        name=row.name,
        issuer=row.issuer,
        theme=row.theme,
        expense_ratio=row.expense_ratio,
        exchange=row.exchange,
        aum=row.aum,
        in_signal_universe=row.in_signal_universe,
        signal_universe_reason=row.signal_universe_reason,
        inception_date=row.inception_date,
        is_active_etf=row.is_active_etf,
        discloses_daily=row.discloses_daily,
        currency=row.currency,
        description=row.description,
    )


def to_price(row: EtfPriceORM) -> PricePoint:
    return PricePoint(
        ticker=row.etf.ticker,
        on=row.date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        nav=row.nav,
        volume=row.volume,
    )


def to_holding(row: EtfHoldingORM) -> Holding:
    return Holding(
        ticker=row.etf.ticker,
        as_of_date=row.as_of_date,
        holding_ticker=row.holding_ticker,
        holding_name=row.holding_name,
        weight=row.weight,
        shares=row.shares,
        market_value=row.market_value,
        security_id=row.security_id,
    )


def to_holding_change(row: EtfHoldingChangeORM) -> HoldingChange:
    return HoldingChange(
        ticker=row.etf.ticker,
        as_of_date=row.as_of_date,
        prev_date=row.prev_date,
        holding_ticker=row.holding_ticker,
        holding_name=row.holding_name,
        change_type=row.change_type,
        shares_before=row.shares_before,
        shares_after=row.shares_after,
        shares_delta=row.shares_delta,
        shares_delta_pct=row.shares_delta_pct,
        weight_before=row.weight_before,
        weight_after=row.weight_after,
        weight_delta=row.weight_delta,
        security_id=row.security_id,
    )


def to_metric(row: EtfMetricORM) -> Metric:
    return Metric(
        ticker=row.etf.ticker,
        as_of=row.as_of,
        aum=row.aum,
        return_1m=row.return_1m,
        return_3m=row.return_3m,
        return_ytd=row.return_ytd,
        return_1y=row.return_1y,
    )


def to_collection_run(row: CollectionRunORM) -> CollectionRun:
    return CollectionRun(
        id=row.id,
        job_name=row.job_name,
        status=row.status,
        started_at=row.started_at,
        finished_at=row.finished_at,
        items_processed=row.items_processed,
        error=row.error,
    )


def to_collection_item_log(row: CollectionItemLogORM) -> CollectionItemLog:
    return CollectionItemLog(
        id=row.id,
        run_id=row.run_id,
        etf_id=row.etf_id,
        ticker=row.ticker,
        item_type=row.item_type,
        status=row.status,
        row_count=row.row_count,
        error=row.error,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )
