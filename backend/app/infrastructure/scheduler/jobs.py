from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.pipeline.collect import CollectionAlreadyRunningError, collect_once
from app.config import Settings
from app.infrastructure.db.engine import SessionLocal
from app.infrastructure.db.repositories import SqlAlchemyEtfRepository, SqlAlchemyHoldingRepository

logger = logging.getLogger(__name__)


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        collect_once,
        "cron",
        hour=settings.collect_cron_hour,
        minute=settings.collect_cron_minute,
        id="daily_collect",
        name="Daily ETF holdings collect",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
        kwargs={
            "job_name": "scheduled_collect",
            "lookback_days": settings.scheduler_lookback_days,
            "collect_prices": settings.scheduler_collect_prices,
            "collect_holdings": True,
        },
    )
    if settings.scheduler_catch_up_on_startup:
        scheduler.add_job(
            catch_up_stale_holdings,
            "date",
            run_date=datetime.now(UTC),
            id="startup_catch_up_collect",
            name="Startup stale holdings catch-up",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300,
            kwargs={"settings": settings},
        )
    return scheduler


async def catch_up_stale_holdings(settings: Settings) -> bool:
    if not await holdings_are_stale(stale_after_days=settings.scheduler_stale_after_days):
        return False

    try:
        await collect_once(
            job_name="startup_catch_up_collect",
            lookback_days=settings.scheduler_lookback_days,
            collect_prices=settings.scheduler_collect_prices,
            collect_holdings=True,
        )
    except CollectionAlreadyRunningError:
        logger.info("Skipping startup catch-up because another collection is already running")
        return False
    except Exception:
        logger.exception("Startup catch-up collection failed")
        return False
    return True


async def holdings_are_stale(*, stale_after_days: int) -> bool:
    threshold = datetime.now(UTC).date() - timedelta(days=stale_after_days)
    page = 1
    page_size = 500
    async with SessionLocal() as session:
        etfs = SqlAlchemyEtfRepository(session)
        holdings = SqlAlchemyHoldingRepository(session)
        while True:
            batch, total = await etfs.list(page=page, page_size=page_size)
            for etf in batch:
                if not etf.discloses_daily:
                    continue
                latest = await holdings.latest_snapshot_date(etf.ticker)
                if latest is None or latest < threshold:
                    return True
            if page * page_size >= total or not batch:
                return False
            page += 1
