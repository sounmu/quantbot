from __future__ import annotations

from datetime import date

from app.application.services.underlying_security_service import (
    UnderlyingSecurityService,
    incremental_price_lookback_days,
    price_ticker_for_holding,
)
from app.domain.entities import Etf, Holding
from tests.fakes import FakeEtfRepository, FakeHoldingRepository, FakeSecurityRepository


async def test_discovers_priceable_latest_signal_universe_holdings() -> None:
    etfs = FakeEtfRepository()
    holdings = FakeHoldingRepository()
    securities = FakeSecurityRepository()
    service = UnderlyingSecurityService(etfs=etfs, holdings=holdings, securities=securities)

    await etfs.upsert(
        Etf("ARKK", "ARK Innovation ETF", "ARK", in_signal_universe=True)
    )
    await etfs.upsert(
        Etf("AVDV", "Avantis International Small Cap Value", "Avantis", in_signal_universe=True)
    )
    await etfs.upsert(
        Etf("SMALL", "Too Small ETF", "Test", in_signal_universe=False)
    )
    await holdings.upsert_many(
        [
            Holding("ARKK", date(2026, 1, 2), "Apple Inc", 5, "aapl", shares=10),
            Holding("ARKK", date(2026, 1, 2), "Berkshire Hathaway", 4, "BRK/B", shares=4),
            Holding(
                "ARKK",
                date(2026, 1, 2),
                "Tesla Inc",
                3,
                "TSLA",
                shares=8,
                security_id="US88160R1014",
            ),
            Holding("AVDV", date(2026, 1, 2), "Drax Group PLC", 2, "DRX", shares=7,
                    security_id="GB0009633180"),
            Holding("AVDV", date(2026, 1, 2), "Tickerless US Co", 1, None, shares=5,
                    security_id="US0000000001"),
            Holding(
                "AVDV",
                date(2026, 1, 2),
                "Bank of Queensland Ltd Common Stock",
                1,
                "BOQ",
                shares=5,
                security_id="607624909",
            ),
            Holding("SMALL", date(2026, 1, 2), "Ignored Inc", 1, "IGN", shares=5),
        ]
    )

    discovered, written = await service.refresh_priceable_security_master(benchmark_ticker="QQQ")

    assert written == 4
    assert [(security.security_key, security.ticker) for security in discovered] == [
        ("QQQ", "QQQ"),
        ("AAPL", "AAPL"),
        ("BRK/B", "BRK-B"),
        ("ID:US88160R1014", "TSLA"),
    ]
    assert await securities.get("ID:US88160R1014") is not None


def test_price_ticker_for_holding_excludes_tickerless_and_non_us_isin() -> None:
    assert (
        price_ticker_for_holding(
            Holding("AVDV", date(2026, 1, 2), "Drax", 1, "DRX", security_id="GB0009633180")
        )
        is None
    )
    assert (
        price_ticker_for_holding(
            Holding("ARKK", date(2026, 1, 2), "Tickerless", 1, None)
        )
        is None
    )
    assert price_ticker_for_holding(
        Holding("ARKK", date(2026, 1, 2), "Berkshire", 1, "BRK/B")
    ) == "BRK-B"


def test_price_ticker_for_holding_excludes_currency_and_local_market_symbols() -> None:
    assert (
        price_ticker_for_holding(
            Holding(
                "AVDV",
                date(2026, 1, 2),
                "GBP Spot FX",
                0,
                "GBP999999",
                security_id="GBP999999",
            )
        )
        is None
    )
    assert (
        price_ticker_for_holding(
            Holding(
                "CGGR",
                date(2026, 1, 2),
                "SK HYNIX INC COMMON STOCK KRW5000.0",
                1,
                "A000660",
                security_id="645026907.0",
            )
        )
        is None
    )
    assert (
        price_ticker_for_holding(
            Holding("AVDV", date(2026, 1, 2), "JD Sports Fashion PLC", 1, "JD.")
        )
        is None
    )
    assert (
        price_ticker_for_holding(
            Holding("AVDV", date(2026, 1, 2), "Ensilica PLC", 1, "ENSIGBX")
        )
        is None
    )
    assert (
        price_ticker_for_holding(
            Holding("ARKW", date(2026, 1, 2), "3IQ ETHER STAKING ETF", 1, "ETHQ/U")
        )
        is None
    )
    assert price_ticker_for_holding(
        Holding("TCAF", date(2026, 1, 2), "NVIDIA CORP COMMON STOCK USD.001", 1, "NVDA")
    ) == "NVDA"


def test_incremental_price_lookback_days_skips_current_and_caps_old_ranges() -> None:
    today = date(2026, 6, 27)

    assert incremental_price_lookback_days(
        None,
        requested_lookback_days=365,
        overlap_days=7,
        today=today,
    ) == 365
    assert incremental_price_lookback_days(
        date(2026, 6, 27),
        requested_lookback_days=365,
        overlap_days=7,
        today=today,
    ) is None
    assert incremental_price_lookback_days(
        date(2026, 6, 26),
        requested_lookback_days=365,
        overlap_days=7,
        today=today,
    ) == 8
    assert incremental_price_lookback_days(
        date(2024, 1, 1),
        requested_lookback_days=365,
        overlap_days=7,
        today=today,
    ) == 365
