from __future__ import annotations

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.config import get_settings
from app.interfaces.api import admin


@pytest.fixture(autouse=True)
def admin_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token-for-tests")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_require_admin_uses_exact_token() -> None:
    admin._require_admin("secret-token-for-tests")

    with pytest.raises(HTTPException) as exc:
        admin._require_admin("secret")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_trigger_collect_schedules_requested_options(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_collect_once(**_: object) -> int:
        return 0

    async def fake_acquire_collection_lock() -> bool:
        return True

    monkeypatch.setattr(admin, "collect_once", fake_collect_once)
    monkeypatch.setattr(admin, "acquire_collection_lock", fake_acquire_collection_lock)

    background_tasks = BackgroundTasks()
    response = await admin.trigger_collect(
        background_tasks,
        with_prices=True,
        lookback_days=42,
        x_admin_token="secret-token-for-tests",
    )

    assert response == {
        "status": "scheduled",
        "job_name": "manual_collect_with_prices",
        "with_prices": True,
        "lookback_days": 42,
    }
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].kwargs == {
        "job_name": "manual_collect_with_prices",
        "lookback_days": 42,
        "collect_prices": True,
        "collect_holdings": True,
        "lock_already_acquired": True,
    }


@pytest.mark.asyncio
async def test_trigger_collect_rejects_when_collection_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_acquire_collection_lock() -> bool:
        return False

    monkeypatch.setattr(admin, "acquire_collection_lock", fake_acquire_collection_lock)

    with pytest.raises(HTTPException) as exc:
        await admin.trigger_collect(
            BackgroundTasks(),
            with_prices=False,
            lookback_days=365,
            x_admin_token="secret-token-for-tests",
        )

    assert exc.value.status_code == 409
