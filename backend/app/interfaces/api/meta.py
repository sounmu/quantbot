from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.services.etf_service import EtfService
from app.interfaces.deps import get_etf_service

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/issuers", response_model=list[str])
async def list_issuers(service: EtfService = Depends(get_etf_service)) -> list[str]:
    return await service.issuers()


@router.get("/themes", response_model=list[str])
async def list_themes(service: EtfService = Depends(get_etf_service)) -> list[str]:
    return await service.themes()

