from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.infrastructure.db.orm_models import Base, CollectionRunORM, EtfHoldingORM, EtfORM
from app.interfaces.api import admin


class _FakeRequest:
    def __init__(self) -> None:
        self.client = type("_Addr", (), {"host": "127.0.0.1"})()


@pytest.fixture(autouse=True)
def admin_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token-for-tests")
    monkeypatch.setenv("SCHEDULER_STALE_AFTER_DAYS", "1")
    get_settings.cache_clear()
    admin._rate_limit_store.clear()
    yield
    admin._rate_limit_store.clear()
    get_settings.cache_clear()


def test_require_admin_uses_exact_token() -> None:
    admin._require_admin("secret-token-for-tests")

    with pytest.raises(HTTPException) as exc:
        admin._require_admin("secret")

    assert exc.value.status_code == 401


def test_require_admin_rejects_when_email_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWED_EMAILS", "admin@example.com")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        admin._require_admin("secret-token-for-tests", x_admin_email="other@example.com")

    assert exc.value.status_code == 403


def test_require_admin_allows_configured_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWED_EMAILS", "admin@example.com,ops@example.com")
    get_settings.cache_clear()

    admin._require_admin("secret-token-for-tests", x_admin_email="ops@example.com")


def test_require_admin_rejects_when_group_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_ALLOWED_GROUPS", "admin-team")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        admin._require_admin("secret-token-for-tests", x_admin_group="other-team")

    assert exc.value.status_code == 403


def test_rate_limit_blocks_after_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()

    # Clear the bucket
    admin._rate_limit_store.clear()
    req = _FakeRequest()

    # First 3 should succeed
    for _ in range(3):
        admin._check_rate_limit("token", req)

    # 4th should raise 429
    with pytest.raises(HTTPException) as exc:
        admin._check_rate_limit("token", req)

    assert exc.value.status_code == 429


def test_rate_limit_uses_ip_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()

    admin._rate_limit_store.clear()
    req = _FakeRequest()

    admin._check_rate_limit(None, req)

    with pytest.raises(HTTPException) as exc:
        admin._check_rate_limit(None, req)

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_trigger_collect_schedules_requested_options(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_collect_once(**_: object) -> int:
        return 0

    async def fake_acquire_collection_lock() -> bool:
        return True

    monkeypatch.setattr(admin, "collect_once", fake_collect_once)
    monkeypatch.setattr(admin, "acquire_collection_lock", fake_acquire_collection_lock)
    monkeypatch.setattr(admin, "_check_rate_limit", lambda *args: None)

    background_tasks = BackgroundTasks()
    response = await admin.trigger_collect(
        background_tasks,
        request=_FakeRequest(),
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
    monkeypatch.setattr(admin, "_check_rate_limit", lambda *args: None)

    with pytest.raises(HTTPException) as exc:
        await admin.trigger_collect(
            BackgroundTasks(),
            request=_FakeRequest(),
            with_prices=False,
            lookback_days=365,
            x_admin_token="secret-token-for-tests",
        )

    assert exc.value.status_code == 409


async def _memory_session_factory() -> async_sessionmaker[AsyncSession]:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_collection_quality_returns_etf_staleness_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration-style: seed DB with ETFs, holdings, and an error run."""
    import app.infrastructure.db.engine as engine_module

    session_factory = await _memory_session_factory()
    monkeypatch.setattr(engine_module, "SessionLocal", session_factory)
    monkeypatch.setattr(admin, "_check_rate_limit", lambda *args: None)
    get_settings.cache_clear()

    async with session_factory() as session:
        # Seed ETFs
        session.add(
            EtfORM(
                id=10,
                ticker="DYNF",
                name="iShares Factor ETF",
                issuer="BlackRock",
                discloses_daily=True,
            )
        )
        session.add(
            EtfORM(
                id=20,
                ticker="ARKK",
                name="ARK Innovation ETF",
                issuer="ARK",
                discloses_daily=True,
            )
        )
        session.add(
            EtfORM(
                id=30,
                ticker="CLOSED",
                name="A closed-end fund",
                issuer="SomeIssuer",
                discloses_daily=False,
            )
        )
        # Fresh holding for DYNF (today), stale for ARKK (30 days ago)
        today = date.today()
        session.add(
            EtfHoldingORM(
                etf_id=10,
                as_of_date=today,
                holding_key="ID:NVDA",
                holding_ticker="NVDA",
                holding_name="NVIDIA CORP",
                weight=8.0,
                shares=1000,
            )
        )
        session.add(
            EtfHoldingORM(
                etf_id=10,
                as_of_date=today,
                holding_key="ID:CASH",
                holding_ticker=None,
                holding_name="CASH",
                weight=0.01,
                shares=None,
            )
        )
        session.add(
            EtfHoldingORM(
                etf_id=20,
                as_of_date=today - timedelta(days=30),
                holding_key="ID:TSLA",
                holding_ticker="TSLA",
                holding_name="TESLA INC",
                weight=10.0,
                shares=500,
            )
        )
        # Error run
        session.add(
            CollectionRunORM(
                job_name="scheduled_collect",
                status="partial",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                items_processed=10,
                error="ARKK holdings: timeout\nDYNF prices: rate-limit",
            )
        )
        await session.commit()

    response = await admin.collection_quality(
        request=_FakeRequest(),
        x_admin_token="secret-token-for-tests",
        session=session_factory(),
    )

    assert response.stale_after_days == 1
    assert len(response.items) == 3

    dynf = next(item for item in response.items if item.ticker == "DYNF")
    assert not dynf.is_stale
    assert dynf.latest_holdings_date == date.today()
    assert dynf.total_holdings_count == 2
    assert dynf.missing_shares_count == 1
    assert dynf.last_collection_error == "rate-limit"

    arkk = next(item for item in response.items if item.ticker == "ARKK")
    assert arkk.is_stale
    assert arkk.last_collection_error == "timeout"

    closed = next(item for item in response.items if item.ticker == "CLOSED")
    assert not closed.is_stale  # non-daily funds are never stale
    assert closed.total_holdings_count == 0

    assert response.provider_errors.get("BlackRock") == "rate-limit"
    assert response.provider_errors.get("ARK") == "timeout"
    assert response.provider_errors.get("SomeIssuer") is None


@pytest.mark.asyncio
async def test_collection_quality_counts_only_latest_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """total/missing counts must reflect the latest snapshot only, not the
    ETF's entire snapshot history."""
    import app.infrastructure.db.engine as engine_module

    session_factory = await _memory_session_factory()
    monkeypatch.setattr(engine_module, "SessionLocal", session_factory)
    monkeypatch.setattr(admin, "_check_rate_limit", lambda *args: None)
    get_settings.cache_clear()

    today = date.today()
    async with session_factory() as session:
        session.add(
            EtfORM(id=10, ticker="DYNF", name="iShares Factor ETF", issuer="BlackRock")
        )
        # Old snapshot: 3 rows, 2 missing shares — must be ignored.
        for i, key in enumerate(("ID:OLD1", "ID:OLD2", "ID:OLD3")):
            session.add(
                EtfHoldingORM(
                    etf_id=10,
                    as_of_date=today - timedelta(days=1),
                    holding_key=key,
                    holding_name=f"OLD{i}",
                    weight=1.0,
                    shares=None if i < 2 else 5,
                )
            )
        # Latest snapshot: 2 rows, 1 missing shares — counts should match these.
        session.add(
            EtfHoldingORM(
                etf_id=10,
                as_of_date=today,
                holding_key="ID:NVDA",
                holding_name="NVIDIA",
                weight=8.0,
                shares=1000,
            )
        )
        session.add(
            EtfHoldingORM(
                etf_id=10,
                as_of_date=today,
                holding_key="ID:CASH",
                holding_name="CASH",
                weight=0.01,
                shares=None,
            )
        )
        await session.commit()

    response = await admin.collection_quality(
        request=_FakeRequest(),
        x_admin_token="secret-token-for-tests",
        session=session_factory(),
    )

    dynf = next(item for item in response.items if item.ticker == "DYNF")
    assert dynf.latest_holdings_date == today
    assert dynf.total_holdings_count == 2  # latest snapshot only, not 5
    assert dynf.missing_shares_count == 1  # latest snapshot only, not 3
