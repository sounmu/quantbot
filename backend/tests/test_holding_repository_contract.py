from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.domain.entities import (
    Etf,
    Holding,
    HoldingChange,
    Metric,
    PricePoint,
    Security,
    SecurityPrice,
    SignalDaily,
)
from app.domain.value_objects import ChangeType
from app.infrastructure.db.orm_models import Base
from app.infrastructure.db.repositories import (
    SqlAlchemyEtfRepository,
    SqlAlchemyHoldingRepository,
    SqlAlchemyMetricRepository,
    SqlAlchemyPriceRepository,
    SqlAlchemySecurityPriceRepository,
    SqlAlchemySecurityRepository,
    SqlAlchemySignalDailyRepository,
    SqlAlchemyHoldingChangeRepository,
)


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


@pytest.mark.asyncio
async def test_metric_repository_preserves_existing_aum_on_return_only_update() -> None:
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
        metrics = SqlAlchemyMetricRepository(session)
        await etfs.upsert(Etf(ticker="DYNF", name="DYNF", issuer="BlackRock"))
        await metrics.upsert(Metric(ticker="DYNF", as_of=date(2026, 1, 2), aum=200_000_000))
        await metrics.upsert(
            Metric(ticker="DYNF", as_of=date(2026, 1, 3), aum=None, return_1y=12.5)
        )
        await session.commit()

        metric = await metrics.get("DYNF")
        etf = await etfs.get("DYNF")
        assert metric is not None
        assert metric.aum == 200_000_000
        assert metric.return_1y == 12.5
        assert etf is not None
        assert etf.aum == 200_000_000

    await engine.dispose()


@pytest.mark.asyncio
async def test_holding_repository_distinguishes_cross_listed_tickers_by_security_id() -> None:
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
        await etfs.upsert(Etf(ticker="AVDV", name="Avantis Intl Small Cap Value", issuer="Avantis"))
        # Two different companies sharing the local ticker "DRX" must coexist in one snapshot.
        await holdings.upsert_many(
            [
                Holding(
                    "AVDV", date(2026, 1, 2), "DRAX GROUP PLC", 1.0, "DRX", shares=100,
                    security_id="GB0009633180",
                ),
                Holding(
                    "AVDV", date(2026, 1, 2), "ADF GROUP INC", 0.5, "DRX", shares=50,
                    security_id="CA0008681011",
                ),
            ]
        )
        await session.commit()

        latest = await holdings.latest("AVDV")
        assert len(latest) == 2

        history = await holdings.position_history("AVDV", "ID:GB0009633180")
        assert [holding.holding_name for holding in history] == ["DRAX GROUP PLC"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_price_repository_upserts_existing_dates() -> None:
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
        prices = SqlAlchemyPriceRepository(session)
        await etfs.upsert(Etf(ticker="TEST", name="Test ETF", issuer="Test"))
        await prices.upsert_many(
            [
                PricePoint("TEST", date(2026, 1, 2), close=100, volume=10),
                PricePoint("TEST", date(2026, 1, 3), close=101, volume=11),
            ]
        )
        await prices.upsert_many(
            [
                PricePoint("TEST", date(2026, 1, 3), close=102, volume=12),
                PricePoint("UNKNOWN", date(2026, 1, 3), close=1),
            ]
        )
        await session.commit()

        series = await prices.series("TEST", range_="max")
        assert [(point.on, point.close, point.volume) for point in series] == [
            (date(2026, 1, 2), 100, 10),
            (date(2026, 1, 3), 102, 12),
        ]

    await engine.dispose()


@pytest.mark.asyncio
async def test_security_price_repository_upserts_existing_dates() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        securities = SqlAlchemySecurityRepository(session)
        prices = SqlAlchemySecurityPriceRepository(session)
        await securities.upsert_many(
            [
                Security(
                    security_key="AAPL",
                    ticker="AAPL",
                    name="Apple Inc",
                    first_seen=date(2026, 1, 2),
                )
            ]
        )
        await prices.upsert_many(
            [
                SecurityPrice("AAPL", date(2026, 1, 2), close=100, adj_close=99, volume=10),
                SecurityPrice("AAPL", date(2026, 1, 3), close=101, adj_close=100, volume=11),
            ]
        )
        await prices.upsert_many(
            [
                SecurityPrice("AAPL", date(2026, 1, 3), close=102, adj_close=101, volume=12),
                SecurityPrice("UNKNOWN", date(2026, 1, 3), close=1, adj_close=1),
            ]
        )
        await session.commit()

        assert await prices.latest_date("AAPL") == date(2026, 1, 3)
        series = await prices.series("AAPL")
        assert [(point.on, point.close, point.adj_close, point.volume) for point in series] == [
            (date(2026, 1, 2), 100, 99, 10),
            (date(2026, 1, 3), 102, 101, 12),
        ]

    await engine.dispose()


@pytest.mark.asyncio
async def test_signal_repositories_materialize_priceable_signal_universe_changes() -> None:
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
        securities = SqlAlchemySecurityRepository(session)
        changes = SqlAlchemyHoldingChangeRepository(session)
        signals = SqlAlchemySignalDailyRepository(session)

        await etfs.upsert(
            Etf("ARKK", "ARK Innovation ETF", "ARK", in_signal_universe=True)
        )
        await etfs.upsert(
            Etf("SMALL", "Small ETF", "Test", in_signal_universe=False)
        )
        await securities.upsert_many(
            [
                Security(
                    security_key="TSLA",
                    ticker="TSLA",
                    name="Tesla Inc",
                    first_seen=date(2026, 1, 2),
                )
            ]
        )
        await changes.upsert_many(
            [
                HoldingChange(
                    "ARKK",
                    date(2026, 1, 2),
                    date(2026, 1, 1),
                    "Tesla Inc",
                    "TSLA",
                    ChangeType.INCREASE,
                    100,
                    110,
                    10,
                    10,
                    1,
                    1.2,
                    0.2,
                )
            ]
        )
        await changes.upsert_many(
            [
                HoldingChange(
                    "SMALL",
                    date(2026, 1, 2),
                    date(2026, 1, 1),
                    "Tesla Inc",
                    "TSLA",
                    ChangeType.INCREASE,
                    100,
                    110,
                    10,
                    10,
                    1,
                    1.2,
                    0.2,
                )
            ]
        )
        await signals.replace_for_dates(
            [date(2026, 1, 2)],
            [
                SignalDaily(
                    security_key="TSLA",
                    as_of_date=date(2026, 1, 2),
                    security_ticker="TSLA",
                    security_name="Tesla Inc",
                    n_buying=1,
                    n_selling=0,
                    net_shares_flow=10,
                    net_dollar_flow=2_000,
                    conviction_score=1,
                )
            ],
        )
        await session.commit()

        source_changes = await changes.signal_sources(as_of_date=date(2026, 1, 2))
        assert [change.ticker for change in source_changes] == ["ARKK"]

        participants = await changes.signal_participants("TSLA", as_of_date=date(2026, 1, 2))
        assert [(participant.etf_ticker, participant.direction) for participant in participants] == [
            ("ARKK", "BUY")
        ]

        daily = await signals.daily(as_of_date=date(2026, 1, 2))
        assert daily[0].security_ticker == "TSLA"
        assert daily[0].conviction_score == 1

    await engine.dispose()
