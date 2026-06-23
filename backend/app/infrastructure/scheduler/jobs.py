from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.pipeline.collect import collect_once
from app.config import Settings


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
    return scheduler
