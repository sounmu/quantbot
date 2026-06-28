from __future__ import annotations

from datetime import date

import pytest

from app.application.services.universe_service import SignalUniversePolicy, refresh_signal_universe
from app.domain.entities import Etf, Metric
from tests.fakes import FakeEtfRepository, FakeMetricRepository


def test_signal_universe_policy_accepts_major_exchange_and_min_aum() -> None:
    policy = SignalUniversePolicy(min_aum=100_000_000, exchanges=["NYSEArca", "Cboe US"])

    decision = policy.evaluate(
        Etf(
            ticker="ARKK",
            name="ARK Innovation ETF",
            issuer="ARK",
            exchange="Cboe US",
            discloses_daily=True,
        ),
        aum=7_000_000_000,
    )

    assert decision.in_universe
    assert decision.reason == "eligible"


def test_signal_universe_policy_rejects_missing_or_small_metadata() -> None:
    policy = SignalUniversePolicy(min_aum=100_000_000, exchanges=["NYSEArca"])

    low_aum = policy.evaluate(
        Etf(
            ticker="TINY",
            name="Tiny ETF",
            issuer="Issuer",
            exchange="NYSEArca",
            discloses_daily=True,
        ),
        aum=10_000_000,
    )
    wrong_exchange = policy.evaluate(
        Etf(
            ticker="OTC",
            name="OTC ETF",
            issuer="Issuer",
            exchange="OTC",
            discloses_daily=True,
        ),
        aum=200_000_000,
    )

    assert low_aum.reason == "aum_below_min"
    assert wrong_exchange.reason == "exchange_not_allowed"


def test_signal_universe_policy_rejects_non_us_or_non_equity_strategies() -> None:
    policy = SignalUniversePolicy(min_aum=100_000_000, exchanges=["NYSEArca"])

    international = policy.evaluate(
        Etf(
            ticker="AVDV",
            name="Avantis International Small Cap Value ETF",
            issuer="Avantis",
            theme="International Value",
            exchange="NYSEArca",
            discloses_daily=True,
        ),
        aum=20_000_000_000,
    )
    fixed_income = policy.evaluate(
        Etf(
            ticker="TOTL",
            name="SPDR DoubleLine Total Return Tactical ETF",
            issuer="State Street",
            theme="Fixed Income",
            exchange="NYSEArca",
            discloses_daily=True,
        ),
        aum=4_000_000_000,
    )
    preferred = policy.evaluate(
        Etf(
            ticker="PFFA",
            name="Virtus InfraCap U.S. Preferred Stock ETF",
            issuer="Virtus",
            theme="Preferred Income",
            exchange="NYSEArca",
            discloses_daily=True,
        ),
        aum=2_000_000_000,
    )

    assert international.reason == "non_us_equity"
    assert fixed_income.reason == "non_equity_strategy"
    assert preferred.reason == "non_equity_strategy"


@pytest.mark.asyncio
async def test_refresh_signal_universe_recalculates_from_metric_aum() -> None:
    etfs = FakeEtfRepository()
    metrics = FakeMetricRepository()
    await etfs.upsert(
        Etf(
            ticker="DYNF",
            name="iShares Factor ETF",
            issuer="BlackRock",
            exchange="NYSEArca",
            discloses_daily=True,
        )
    )
    await metrics.upsert(Metric(ticker="DYNF", as_of=date.today(), aum=200_000_000))

    updated = await refresh_signal_universe(
        etfs,
        metrics,
        SignalUniversePolicy(min_aum=100_000_000, exchanges=["NYSE Arca"]),
    )

    dynf = await etfs.get("DYNF")
    assert updated == 1
    assert dynf is not None
    assert dynf.aum == 200_000_000
    assert dynf.in_signal_universe
    assert dynf.signal_universe_reason == "eligible"
