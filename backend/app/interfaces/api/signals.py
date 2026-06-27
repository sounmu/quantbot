from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.application.services.signal_service import SignalService, SignalWithParticipants
from app.domain.entities import SignalDaily, SignalParticipant
from app.interfaces.deps import get_signal_service
from app.interfaces.schemas.signal import (
    SignalDailyResponse,
    SignalParticipantResponse,
    SignalSecurityHistoryResponse,
)

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/daily", response_model=list[SignalDailyResponse])
async def daily_signals(
    as_of_date: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, ge=1, le=500),
    service: SignalService = Depends(get_signal_service),
) -> list[SignalDailyResponse]:
    signals = await service.daily(as_of_date=as_of_date, limit=limit)
    return [_to_signal_response(signal) for signal in signals]


@router.get("/security/{security_key:path}", response_model=list[SignalSecurityHistoryResponse])
async def security_signals(
    security_key: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: SignalService = Depends(get_signal_service),
) -> list[SignalSecurityHistoryResponse]:
    history = await service.for_security(security_key, limit=limit)
    return [_to_history_response(item) for item in history]


def _to_history_response(item: SignalWithParticipants) -> SignalSecurityHistoryResponse:
    signal = _to_signal_response(item.signal)
    return SignalSecurityHistoryResponse(
        **signal.model_dump(),
        participants=[
            _to_participant_response(participant) for participant in item.participants
        ],
    )


def _to_signal_response(signal: SignalDaily) -> SignalDailyResponse:
    return SignalDailyResponse(
        security_key=signal.security_key,
        as_of_date=signal.as_of_date,
        security_ticker=signal.security_ticker,
        security_name=signal.security_name,
        n_buying=signal.n_buying,
        n_selling=signal.n_selling,
        net_shares_flow=signal.net_shares_flow,
        net_dollar_flow=signal.net_dollar_flow,
        conviction_score=signal.conviction_score,
    )


def _to_participant_response(participant: SignalParticipant) -> SignalParticipantResponse:
    return SignalParticipantResponse(
        etf_ticker=participant.etf_ticker,
        etf_name=participant.etf_name,
        issuer=participant.issuer,
        direction=participant.direction,
        change_type=participant.change_type,
        shares_delta=participant.shares_delta,
        shares_delta_pct=participant.shares_delta_pct,
        weight_delta=participant.weight_delta,
    )
