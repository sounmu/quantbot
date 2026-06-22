from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.services.etf_service import EtfService
from app.domain.value_objects import ChangeType
from app.interfaces.api.etfs import _to_change_response
from app.interfaces.deps import get_etf_service
from app.interfaces.schemas.change import HoldingChangeResponse

router = APIRouter(prefix="/api/changes", tags=["changes"])


@router.get("/recent", response_model=list[HoldingChangeResponse])
async def recent_changes(
    types: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: EtfService = Depends(get_etf_service),
) -> list[HoldingChangeResponse]:
    change_types = (
        [item.strip().upper() for item in types.split(",") if item.strip()]
        if types
        else [ChangeType.NEW, ChangeType.EXIT, ChangeType.INCREASE, ChangeType.DECREASE]
    )
    changes = await service.get_recent_changes(limit=limit, change_types=change_types)
    return [_to_change_response(change) for change in changes]
