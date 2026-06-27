from __future__ import annotations

from datetime import date

import pytest

from app.application.services.evaluation_service import (
    EvaluationService,
    benchmark_security_key,
    compute_signal_outcomes,
    summarize_performance,
)
from app.domain.entities import SecurityPrice, SignalDaily
from tests.fakes import (
    FakeSecurityPriceRepository,
    FakeSignalDailyRepository,
    FakeSignalOutcomeRepository,
)


def test_compute_signal_outcomes_uses_only_prices_after_signal_date() -> None:
    signal = _signal("TSLA", date(2026, 1, 1), conviction=2)
    outcomes = compute_signal_outcomes(
        [signal],
        {
            "TSLA": [
                SecurityPrice("TSLA", date(2026, 1, 1), close=999, adj_close=999),
                SecurityPrice("TSLA", date(2026, 1, 2), close=100, adj_close=100),
                SecurityPrice("TSLA", date(2026, 1, 3), close=110, adj_close=110),
            ],
            "QQQ": [
                SecurityPrice("QQQ", date(2026, 1, 1), close=999, adj_close=999),
                SecurityPrice("QQQ", date(2026, 1, 2), close=100, adj_close=100),
                SecurityPrice("QQQ", date(2026, 1, 3), close=105, adj_close=105),
            ],
        },
        benchmark_key="QQQ",
        horizons=[1],
    )

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.start_date == date(2026, 1, 2)
    assert outcome.end_date == date(2026, 1, 3)
    assert outcome.stock_return == pytest.approx(0.10)
    assert outcome.benchmark_return == pytest.approx(0.05)
    assert outcome.excess_return == pytest.approx(0.05)


async def test_evaluation_service_recomputes_positive_buy_signal_outcomes_and_summary() -> None:
    signals = FakeSignalDailyRepository()
    prices = FakeSecurityPriceRepository()
    outcomes = FakeSignalOutcomeRepository()
    service = EvaluationService(signals=signals, security_prices=prices, outcomes=outcomes)

    await signals.replace_for_dates(
        [date(2026, 1, 1)],
        [
            _signal("TSLA", date(2026, 1, 1), conviction=2),
            _signal("ROKU", date(2026, 1, 1), conviction=-1),
        ],
    )
    await prices.upsert_many(
        [
            SecurityPrice("TSLA", date(2026, 1, 2), close=100, adj_close=100),
            SecurityPrice("TSLA", date(2026, 1, 3), close=110, adj_close=110),
            SecurityPrice("QQQ", date(2026, 1, 2), close=100, adj_close=100),
            SecurityPrice("QQQ", date(2026, 1, 3), close=105, adj_close=105),
        ]
    )

    written = await service.recompute(benchmark_ticker="QQQ", horizons=[1])

    assert written == 1
    performance = await service.performance(bucket="conviction_2_plus", horizon_days=1)
    assert performance[0].sample_size == 1
    assert performance[0].hit_rate == 1
    assert performance[0].average_excess_return == pytest.approx(0.05)

    security = await service.security("TSLA")
    assert security[0].excess_return == pytest.approx(0.05)


def test_summarize_performance_calculates_hit_rate_median_and_ic() -> None:
    outcomes = [
        compute_signal_outcomes(
            [_signal("A", date(2026, 1, 1), conviction=1)],
            _price_map("A", 100, 102, benchmark_end=101),
            benchmark_key="QQQ",
            horizons=[1],
        )[0],
        compute_signal_outcomes(
            [_signal("B", date(2026, 1, 1), conviction=2)],
            _price_map("B", 100, 105, benchmark_end=101),
            benchmark_key="QQQ",
            horizons=[1],
        )[0],
        compute_signal_outcomes(
            [_signal("C", date(2026, 1, 1), conviction=3)],
            _price_map("C", 100, 106, benchmark_end=101),
            benchmark_key="QQQ",
            horizons=[1],
        )[0],
    ]

    summary = summarize_performance(outcomes, bucket="all", horizon_days=1)

    assert summary.sample_size == 3
    assert summary.hit_rate == 1
    assert summary.median_excess_return == pytest.approx(0.04)
    assert summary.information_coefficient == pytest.approx(1.0)


def test_benchmark_security_key_reuses_holding_key_policy() -> None:
    assert benchmark_security_key("qqq") == "QQQ"


def _signal(security_key: str, as_of_date: date, *, conviction: float) -> SignalDaily:
    return SignalDaily(
        security_key=security_key,
        as_of_date=as_of_date,
        security_ticker=security_key,
        security_name=f"{security_key} Inc",
        n_buying=max(int(conviction), 0),
        n_selling=0 if conviction > 0 else 1,
        net_shares_flow=100,
        net_dollar_flow=10_000,
        conviction_score=conviction,
    )


def _price_map(
    security_key: str,
    stock_start: float,
    stock_end: float,
    *,
    benchmark_end: float,
) -> dict[str, list[SecurityPrice]]:
    return {
        security_key: [
            SecurityPrice(security_key, date(2026, 1, 2), close=stock_start, adj_close=stock_start),
            SecurityPrice(security_key, date(2026, 1, 3), close=stock_end, adj_close=stock_end),
        ],
        "QQQ": [
            SecurityPrice("QQQ", date(2026, 1, 2), close=100, adj_close=100),
            SecurityPrice("QQQ", date(2026, 1, 3), close=benchmark_end, adj_close=benchmark_end),
        ],
    }
