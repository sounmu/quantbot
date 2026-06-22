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
        minute=0,
        id="daily_collect",
        replace_existing=True,
    )
    return scheduler

