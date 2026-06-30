from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

FlowAdjustedValue = Literal["BUY", "HOLD", "SELL"]
ActiveDirectionValue = Literal["BUY", "NEUTRAL", "SELL"]
ActiveIntensityValue = Literal["NONE", "WEAK", "MEDIUM", "STRONG"]
ActiveConfidenceValue = Literal["LOW", "MEDIUM", "HIGH"]


class EtfFlowResponse(BaseModel):
    ticker: str
    as_of_date: date
    prev_date: date
    net_flow: float
    flow_rate: float
    active_buy: float
    active_sell: float
    turnover: float
    creation_r2: float | None = None


class SecurityFlowComponentResponse(BaseModel):
    holding_key: str
    holding_ticker: str | None = None
    delta_shares: float
    passive_shares: float
    active_residual: float
    flow_adjusted: FlowAdjustedValue
    active_direction: ActiveDirectionValue
    active_intensity: ActiveIntensityValue
    active_confidence: ActiveConfidenceValue
    residual_nav_bp: float | None = None
    residual_position_pct: float
