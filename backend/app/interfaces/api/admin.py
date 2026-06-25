from __future__ import annotations

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipeline.collect import acquire_collection_lock, collect_once
from app.config import get_settings
from app.infrastructure.db.engine import get_session
from app.infrastructure.db.repositories import SqlAlchemyCollectionRunRepository
from app.interfaces.schemas.common import CollectionRunResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/collect")
async def trigger_collect(
    background_tasks: BackgroundTasks,
    with_prices: bool = Query(default=False),
    lookback_days: int = Query(default=365, ge=1, le=3650),
    x_admin_token: str | None = Header(default=None),
) -> dict[str, bool | int | str]:
    _require_admin(x_admin_token)
    if not await acquire_collection_lock():
        raise HTTPException(status_code=409, detail="Collection already running")
    job_name = "manual_collect_with_prices" if with_prices else "manual_collect"
    background_tasks.add_task(
        collect_once,
        job_name=job_name,
        lookback_days=lookback_days,
        collect_prices=with_prices,
        collect_holdings=True,
        lock_already_acquired=True,
    )
    return {
        "status": "scheduled",
        "job_name": job_name,
        "with_prices": with_prices,
        "lookback_days": lookback_days,
    }


@router.get("/runs", response_model=list[CollectionRunResponse])
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    x_admin_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[CollectionRunResponse]:
    _require_admin(x_admin_token)
    repo = SqlAlchemyCollectionRunRepository(session)
    runs = await repo.list_recent(limit=limit)
    return [
        CollectionRunResponse(
            id=run.id,
            job_name=run.job_name,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            items_processed=run.items_processed,
            error=_summarize_error(run.error),
        )
        for run in runs
    ]


def _require_admin(token: str | None) -> None:
    settings = get_settings()
    if settings.admin_token in {"", "change-me", "replace-with-a-long-random-token"}:
        raise HTTPException(status_code=503, detail="Admin token is not configured")
    if token is None or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


def _summarize_error(error: str | None) -> str | None:
    if error is None:
        return None
    lines = [line for line in error.splitlines() if line.strip()]
    if not lines:
        return None
    return f"{len(lines)} collection error(s); check server logs for details"
