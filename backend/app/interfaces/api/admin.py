from __future__ import annotations

import re
import secrets
import time
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipeline.collect import acquire_collection_lock, collect_once
from app.config import get_settings
from app.infrastructure.db.engine import get_session
from app.infrastructure.db.orm_models import CollectionRunORM, EtfHoldingORM, EtfORM
from app.infrastructure.db.repositories import (
    SqlAlchemyCollectionItemLogRepository,
    SqlAlchemyCollectionRunRepository,
)
from app.interfaces.schemas.common import (
    CollectionItemLogResponse,
    CollectionQualityResponse,
    CollectionRunResponse,
    EtfQualityItem,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/collect")
async def trigger_collect(
    background_tasks: BackgroundTasks,
    request: Request,
    with_prices: bool = Query(default=False),
    lookback_days: int = Query(default=365, ge=1, le=3650),
    x_admin_token: str | None = Header(default=None),
    x_admin_email: str | None = Header(default=None),
    x_admin_group: str | None = Header(default=None),
) -> dict[str, bool | int | str]:
    _require_admin(x_admin_token, x_admin_email, x_admin_group)
    _check_rate_limit(x_admin_token, request)
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
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    x_admin_token: str | None = Header(default=None),
    x_admin_email: str | None = Header(default=None),
    x_admin_group: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[CollectionRunResponse]:
    _require_admin(x_admin_token, x_admin_email, x_admin_group)
    _check_rate_limit(x_admin_token, request)
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


def _require_admin(
    token: str | None,
    x_admin_email: str | None = None,
    x_admin_group: str | None = None,
) -> None:
    settings = get_settings()
    if settings.admin_token in {"", "change-me", "replace-with-a-long-random-token"}:
        raise HTTPException(status_code=503, detail="Admin token is not configured")
    if token is None or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")

    if settings.allowed_email_set is not None:
        if x_admin_email is None or x_admin_email.strip().lower() not in settings.allowed_email_set:
            raise HTTPException(status_code=403, detail="Admin email not allowed")

    if settings.allowed_group_set is not None:
        if x_admin_group is None or x_admin_group.strip().lower() not in settings.allowed_group_set:
            raise HTTPException(status_code=403, detail="Admin group not allowed")


# In-memory rate limiting (shared across workers in single-process only)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(token: str | None, request: Request) -> None:
    settings = get_settings()
    max_per_minute = settings.admin_rate_limit_per_minute
    key = token or request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - 60

    bucket = _rate_limit_store[key]
    bucket[:] = [ts for ts in bucket if ts > window_start]
    bucket.append(now)

    if len(bucket) > max_per_minute:
        raise HTTPException(status_code=429, detail="Too many admin requests")


@router.get("/dashboard/quality", response_model=CollectionQualityResponse)
async def collection_quality(
    request: Request,
    x_admin_token: str | None = Header(default=None),
    x_admin_email: str | None = Header(default=None),
    x_admin_group: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> CollectionQualityResponse:
    _require_admin(x_admin_token, x_admin_email, x_admin_group)
    _check_rate_limit(x_admin_token, request)
    settings = get_settings()
    threshold = datetime.now(UTC).date() - timedelta(days=settings.scheduler_stale_after_days)

    # All ETFs
    etf_rows = (await session.scalars(select(EtfORM).order_by(EtfORM.ticker))).all()

    # Latest holdings date per ETF, with counts scoped to that latest snapshot
    # only (not aggregated across the ETF's entire snapshot history).
    etf_ids = [etf.id for etf in etf_rows]
    latest_dates: dict[int, tuple[date | None, int, int]] = {}
    if etf_ids:
        latest_sub = (
            select(
                EtfHoldingORM.etf_id.label("etf_id"),
                func.max(EtfHoldingORM.as_of_date).label("latest_date"),
            )
            .where(EtfHoldingORM.etf_id.in_(etf_ids))
            .group_by(EtfHoldingORM.etf_id)
        ).subquery()
        stmt = (
            select(
                latest_sub.c.etf_id,
                latest_sub.c.latest_date,
                func.count(EtfHoldingORM.id).label("total_count"),
                func.sum(
                    case((EtfHoldingORM.shares.is_(None), 1), else_=0)
                ).label("missing_count"),
            )
            .join(
                EtfHoldingORM,
                (EtfHoldingORM.etf_id == latest_sub.c.etf_id)
                & (EtfHoldingORM.as_of_date == latest_sub.c.latest_date),
            )
            .group_by(latest_sub.c.etf_id, latest_sub.c.latest_date)
        )
        rows = (await session.execute(stmt)).all()
        for row in rows:
            latest_dates[row.etf_id] = (row.latest_date, row.total_count, row.missing_count)

    # Recent collection errors
    error_run = await session.scalar(
        select(CollectionRunORM)
        .where(CollectionRunORM.status.in_(["failed", "partial"]))
        .order_by(CollectionRunORM.started_at.desc())
        .limit(1)
    )
    errors_by_ticker: dict[str, str] = {}
    provider_errors: dict[str, str | None] = {}
    if error_run and error_run.error:
        for line in error_run.error.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^([A-Z0-9]+)\s+(holdings|prices):\s*(.+)", line)
            if match:
                ticker = match.group(1)
                errors_by_ticker[ticker] = match.group(3)
        provider_tickers: dict[str, list[str]] = {}
        for etf in etf_rows:
            provider_tickers.setdefault(etf.issuer, []).append(etf.ticker)
        for issuer, tickers in provider_tickers.items():
            issuer_errors = [errors_by_ticker[t] for t in tickers if t in errors_by_ticker]
            provider_errors[issuer] = "; ".join(issuer_errors) if issuer_errors else None

    items: list[EtfQualityItem] = []
    for etf in etf_rows:
        date_info = latest_dates.get(etf.id, (None, 0, 0))
        latest_date = date_info[0]
        items.append(
            EtfQualityItem(
                ticker=etf.ticker,
                name=etf.name,
                issuer=etf.issuer,
                discloses_daily=etf.discloses_daily,
                latest_holdings_date=latest_date,
                is_stale=etf.discloses_daily
                and (latest_date is None or latest_date < threshold),
                missing_shares_count=date_info[2],
                total_holdings_count=date_info[1],
                last_collection_error=errors_by_ticker.get(etf.ticker),
            )
        )

    return CollectionQualityResponse(
        items=items,
        provider_errors=provider_errors,
        stale_after_days=settings.scheduler_stale_after_days,
    )


@router.get("/runs/{run_id}/items", response_model=list[CollectionItemLogResponse])
async def list_run_items(
    run_id: int,
    request: Request,
    x_admin_token: str | None = Header(default=None),
    x_admin_email: str | None = Header(default=None),
    x_admin_group: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[CollectionItemLogResponse]:
    _require_admin(x_admin_token, x_admin_email, x_admin_group)
    _check_rate_limit(x_admin_token, request)
    repo = SqlAlchemyCollectionItemLogRepository(session)
    logs = await repo.for_run(run_id)
    return [
        CollectionItemLogResponse(
            id=log.id,
            run_id=log.run_id,
            ticker=log.ticker,
            item_type=log.item_type,
            status=log.status,
            row_count=log.row_count,
            error=log.error,
            started_at=log.started_at,
            finished_at=log.finished_at,
        )
        for log in logs
    ]


def _summarize_error(error: str | None) -> str | None:
    if error is None:
        return None
    lines = [line for line in error.splitlines() if line.strip()]
    if not lines:
        return None
    return f"{len(lines)} collection error(s); check server logs for details"
