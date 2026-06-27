from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

SignalDirectionValue = Literal["BUY", "SELL"]


class SignalDailyResponse(BaseModel):
    security_key: str
    as_of_date: date
    security_ticker: str
    security_name: str
    n_buying: int
    n_selling: int
    net_shares_flow: float | None = None
    net_dollar_flow: float | None = None
    conviction_score: float


class SignalParticipantResponse(BaseModel):
    etf_ticker: str
    etf_name: str
    issuer: str
    direction: SignalDirectionValue
    change_type: str
    shares_delta: float | None = None
    shares_delta_pct: float | None = None
    weight_delta: float | None = None


class SignalSecurityHistoryResponse(SignalDailyResponse):
    participants: list[SignalParticipantResponse]
