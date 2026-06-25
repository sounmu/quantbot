from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

ChangeTypeValue = Literal["NEW", "EXIT", "INCREASE", "DECREASE", "UNCHANGED"]


class HoldingChangeResponse(BaseModel):
    ticker: str
    as_of_date: date
    prev_date: date | None = None
    holding_ticker: str | None = None
    holding_name: str
    change_type: ChangeTypeValue
    shares_before: float | None = None
    shares_after: float | None = None
    shares_delta: float | None = None
    shares_delta_pct: float | None = None
    weight_before: float | None = None
    weight_after: float | None = None
    weight_delta: float | None = None


class PositionHistoryPointResponse(BaseModel):
    as_of_date: date
    holding_ticker: str | None = None
    holding_name: str
    shares: float | None = None
    weight: float
    market_value: float | None = None
