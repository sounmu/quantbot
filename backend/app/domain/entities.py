from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Etf:
    ticker: str
    name: str
    issuer: str
    theme: str | None = None
    expense_ratio: float | None = None
    inception_date: date | None = None
    is_active_etf: bool = True
    discloses_daily: bool = True
    currency: str = "USD"
    description: str | None = None


@dataclass(slots=True)
class PricePoint:
    ticker: str
    on: date
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    nav: float | None = None
    volume: int | None = None


@dataclass(slots=True)
class Holding:
    ticker: str
    as_of_date: date
    holding_name: str
    weight: float
    holding_ticker: str | None = None
    shares: float | None = None
    market_value: float | None = None
    security_id: str | None = None


@dataclass(slots=True)
class HoldingChange:
    ticker: str
    as_of_date: date
    prev_date: date | None
    holding_name: str
    holding_ticker: str | None
    change_type: str
    shares_before: float | None
    shares_after: float | None
    shares_delta: float | None
    shares_delta_pct: float | None
    weight_before: float | None
    weight_after: float | None
    weight_delta: float | None
    security_id: str | None = None


@dataclass(slots=True)
class Metric:
    ticker: str
    as_of: date
    aum: float | None = None
    return_1m: float | None = None
    return_3m: float | None = None
    return_ytd: float | None = None
    return_1y: float | None = None


@dataclass(slots=True)
class CollectionRun:
    id: int | None
    job_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    items_processed: int = 0
    error: str | None = None
