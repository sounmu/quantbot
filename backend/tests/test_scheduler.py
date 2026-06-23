from __future__ import annotations

from app.config import Settings
from app.infrastructure.scheduler.jobs import create_scheduler


def test_create_scheduler_registers_daily_collect_job() -> None:
    scheduler = create_scheduler(
        Settings(
            collect_cron_hour=23,
            collect_cron_minute=15,
            scheduler_collect_prices=True,
            scheduler_lookback_days=42,
        )
    )

    job = scheduler.get_job("daily_collect")

    assert job is not None
    assert str(job.trigger) == "cron[hour='23', minute='15']"
    assert job.kwargs == {
        "job_name": "scheduled_collect",
        "lookback_days": 42,
        "collect_prices": True,
        "collect_holdings": True,
    }
    assert job.coalesce is True
    assert job.max_instances == 1
