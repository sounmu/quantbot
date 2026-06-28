from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class HoldingResponse(BaseModel):
    as_of_date: date
    holding_key: str
    holding_ticker: str | None = None
    security_id: str | None = None
    holding_name: str
    weight: float
    shares: float | None = None
    market_value: float | None = None
    change_type: str | None = None
    shares_delta: float | None = None
    shares_delta_pct: float | None = None
    weight_delta: float | None = None
    # Cross-ETF signal for this security on the same date (from signal_daily):
    # how many *other* signal-universe ETFs bought/sold the same name that day.
    signal_n_buying: int | None = None
    signal_n_selling: int | None = None
    signal_conviction: float | None = None
