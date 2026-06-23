from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.domain.entities import Etf, Holding
from app.infrastructure.db.orm_models import Base
from app.infrastructure.db.repositories import SqlAlchemyEtfRepository, SqlAlchemyHoldingRepository


@pytest.mark.asyncio
async def test_holding_repository_snapshot_contract() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        etfs = SqlAlchemyEtfRepository(session)
        holdings = SqlAlchemyHoldingRepository(session)
        await etfs.upsert(Etf(ticker="TEST", name="Test ETF", issuer="Test"))
        await holdings.upsert_many(
            [
                Holding("TEST", date(2026, 1, 2), "Apple Inc", 6.0, "AAPL", shares=10),
                Holding("TEST", date(2026, 1, 2), "Microsoft Corp", 4.0, "MSFT", shares=20),
            ]
        )
        await holdings.upsert_many(
            [
                Holding("TEST", date(2026, 1, 3), "Apple Inc", 7.0, "AAPL", shares=12),
                Holding("TEST", date(2026, 1, 3), "Microsoft Corp", 3.0, "MSFT", shares=18),
            ]
        )
        await session.commit()

        assert await holdings.latest_snapshot_date("TEST") == date(2026, 1, 3)
        assert await holdings.previous_snapshot_date("TEST", date(2026, 1, 3)) == date(2026, 1, 2)
        assert await holdings.snapshot_dates("TEST") == [date(2026, 1, 3), date(2026, 1, 2)]

        latest = await holdings.latest("TEST")
        assert [holding.holding_ticker for holding in latest] == ["AAPL", "MSFT"]

        history = await holdings.position_history("TEST", "AAPL")
        assert [holding.as_of_date for holding in history] == [date(2026, 1, 2), date(2026, 1, 3)]
        assert [holding.shares for holding in history] == [10, 12]

    await engine.dispose()
