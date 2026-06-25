from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.db.orm_models import Base, EtfHoldingORM
from app.infrastructure.db.repositories import SqlAlchemyCollectionItemLogRepository


async def _memory_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_failed_item_log_survives_work_rollback_and_keeps_identity() -> None:
    """A failed item's log must keep its ticker/run_id even after the work it
    logged is rolled back (the regression that produced run_id=0/ticker=unknown).
    """
    factory = await _memory_session_factory()

    async with factory() as session:
        repo = SqlAlchemyCollectionItemLogRepository(session)
        log = await repo.log_start(5, "ARKK", "holdings", etf_id=20)

        # Simulate a partial write that then fails and rolls back, as the
        # collection pipeline does in its per-item except branch.
        session.add(
            EtfHoldingORM(
                etf_id=20,
                as_of_date=date.today(),
                holding_key="ID:TSLA",
                holding_ticker="TSLA",
                holding_name="TESLA INC",
                weight=10.0,
                shares=500,
            )
        )
        await session.rollback()

        result = await repo.log_finish(log.id or 0, status="failed", error="boom")

    assert result is not None
    assert result.ticker == "ARKK"
    assert result.run_id == 5
    assert result.item_type == "holdings"
    assert result.status == "failed"
    assert result.error == "boom"

    # And it is durably persisted (visible from a fresh session via for_run).
    async with factory() as session:
        rows = await SqlAlchemyCollectionItemLogRepository(session).for_run(5)

    assert len(rows) == 1
    assert rows[0].ticker == "ARKK"
    assert rows[0].status == "failed"


@pytest.mark.asyncio
async def test_log_finish_returns_none_for_unknown_id() -> None:
    factory = await _memory_session_factory()
    async with factory() as session:
        repo = SqlAlchemyCollectionItemLogRepository(session)
        assert await repo.log_finish(9999, status="failed", error="x") is None
