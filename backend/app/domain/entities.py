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
    exchange: str | None = None
    aum: float | None = None
    in_signal_universe: bool = False
    signal_universe_reason: str | None = None
    inception_date: date | None = None
    is_active_etf: bool = True
    discloses_daily: bool = True
    currency: str = "USD"
    description: str | None = None


@dataclass(slots=True)
class EtfProfile:
    ticker: str
    as_of: date
    exchange: str | None = None
    aum: float | None = None


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
class Security:
    security_key: str
    ticker: str
    name: str
    first_seen: date
    is_priceable: bool = True


@dataclass(slots=True)
class SecurityPrice:
    security_key: str
    on: date
    close: float
    adj_close: float
    volume: int | None = None


@dataclass(slots=True)
class SignalDaily:
    security_key: str
    as_of_date: date
    security_ticker: str
    security_name: str
    n_buying: int
    n_selling: int
    net_shares_flow: float | None
    net_dollar_flow: float | None
    conviction_score: float


@dataclass(slots=True)
class SignalParticipant:
    etf_ticker: str
    etf_name: str
    issuer: str
    direction: str
    change_type: str
    shares_delta: float | None
    shares_delta_pct: float | None
    weight_delta: float | None


@dataclass(slots=True)
class SignalOutcome:
    security_key: str
    as_of_date: date
    horizon_days: int
    benchmark_key: str
    start_date: date
    end_date: date
    stock_return: float
    benchmark_return: float
    excess_return: float
    signal_score: float


@dataclass(slots=True)
class EtfFlowDaily:
    ticker: str
    as_of_date: date
    prev_date: date
    net_flow: float
    flow_rate: float
    active_buy: float
    active_sell: float
    turnover: float
    creation_r2: float | None


@dataclass(slots=True)
class SecurityFlowComponent:
    holding_key: str
    holding_ticker: str | None
    delta_shares: float
    passive_shares: float
    active_residual: float
    flow_adjusted: str
    active_direction: str
    active_intensity: str
    active_confidence: str
    residual_nav_bp: float | None
    residual_position_pct: float


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


@dataclass(slots=True)
class CollectionItemLog:
    id: int | None
    run_id: int
    ticker: str
    item_type: str
    status: str
    row_count: int
    started_at: datetime
    etf_id: int | None = None
    finished_at: datetime | None = None
    error: str | None = None
