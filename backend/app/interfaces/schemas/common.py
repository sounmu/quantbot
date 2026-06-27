from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class CollectionRunResponse(BaseModel):
    id: int | None
    job_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    items_processed: int
    error: str | None = None


class EtfQualityItem(BaseModel):
    ticker: str
    name: str
    issuer: str
    discloses_daily: bool
    exchange: str | None = None
    aum: float | None = None
    in_signal_universe: bool = False
    signal_universe_reason: str | None = None
    latest_holdings_date: date | None = None
    is_stale: bool = False
    missing_shares_count: int = 0
    total_holdings_count: int = 0
    last_collection_error: str | None = None


class CollectionItemLogResponse(BaseModel):
    id: int | None
    run_id: int
    ticker: str
    item_type: str
    status: str
    row_count: int
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class CollectionQualityResponse(BaseModel):
    items: list[EtfQualityItem]
    provider_errors: dict[str, str | None]
    stale_after_days: int
