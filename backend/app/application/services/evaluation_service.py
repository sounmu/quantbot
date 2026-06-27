from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median

from app.domain.entities import SecurityPrice, SignalDaily, SignalOutcome
from app.domain.repositories import (
    SecurityPriceRepository,
    SignalDailyRepository,
    SignalOutcomeRepository,
)
from app.domain.value_objects import holding_key, normalize_security_key

DEFAULT_HORIZONS = [1, 5, 20, 60]
PERFORMANCE_BUCKETS = ["all", "conviction_1", "conviction_2_plus", "conviction_3_plus"]


@dataclass(slots=True)
class PerformanceSummary:
    bucket: str
    horizon_days: int
    sample_size: int
    hit_rate: float | None
    average_excess_return: float | None
    median_excess_return: float | None
    information_coefficient: float | None


@dataclass(slots=True)
class SecurityAnalysisPoint:
    as_of_date: date
    horizon_days: int
    start_date: date
    end_date: date
    stock_return: float
    benchmark_return: float
    excess_return: float
    signal_score: float


class EvaluationService:
    def __init__(
        self,
        *,
        signals: SignalDailyRepository,
        security_prices: SecurityPriceRepository,
        outcomes: SignalOutcomeRepository,
    ) -> None:
        self._signals = signals
        self._security_prices = security_prices
        self._outcomes = outcomes

    async def recompute(
        self,
        *,
        benchmark_ticker: str,
        horizons: list[int] | None = None,
    ) -> int:
        target_horizons = sorted(set(horizons or DEFAULT_HORIZONS))
        benchmark_key = benchmark_security_key(benchmark_ticker)
        signals = await self._signals.buy_signals()
        price_map: dict[str, list[SecurityPrice]] = {}
        for key in sorted({signal.security_key for signal in signals} | {benchmark_key}):
            price_map[key] = await self._security_prices.series(key)

        outcomes = compute_signal_outcomes(
            signals,
            price_map,
            benchmark_key=benchmark_key,
            horizons=target_horizons,
        )
        return await self._outcomes.replace_all(outcomes)

    async def performance(
        self,
        *,
        bucket: str | None = None,
        horizon_days: int | None = None,
    ) -> list[PerformanceSummary]:
        all_outcomes = await self._outcomes.list(horizon_days=horizon_days)
        buckets = [bucket] if bucket else PERFORMANCE_BUCKETS
        horizons = [horizon_days] if horizon_days else DEFAULT_HORIZONS
        summaries: list[PerformanceSummary] = []
        for target_horizon in horizons:
            horizon_outcomes = [
                outcome for outcome in all_outcomes if outcome.horizon_days == target_horizon
            ]
            for target_bucket in buckets:
                if target_bucket not in PERFORMANCE_BUCKETS:
                    continue
                summaries.append(
                    summarize_performance(
                        [
                            outcome
                            for outcome in horizon_outcomes
                            if _outcome_in_bucket(outcome, target_bucket)
                        ],
                        bucket=target_bucket,
                        horizon_days=target_horizon,
                    )
                )
        return summaries

    async def security(self, security_key: str) -> list[SecurityAnalysisPoint]:
        outcomes = await self._outcomes.list(security_key=security_key)
        return [
            SecurityAnalysisPoint(
                as_of_date=outcome.as_of_date,
                horizon_days=outcome.horizon_days,
                start_date=outcome.start_date,
                end_date=outcome.end_date,
                stock_return=outcome.stock_return,
                benchmark_return=outcome.benchmark_return,
                excess_return=outcome.excess_return,
                signal_score=outcome.signal_score,
            )
            for outcome in outcomes
        ]


def compute_signal_outcomes(
    signals: list[SignalDaily],
    prices_by_security: dict[str, list[SecurityPrice]],
    *,
    benchmark_key: str,
    horizons: list[int],
) -> list[SignalOutcome]:
    benchmark_prices = _prices_by_date(prices_by_security.get(benchmark_key, []))
    outcomes: list[SignalOutcome] = []
    for signal in signals:
        if signal.conviction_score <= 0:
            continue

        series = sorted(
            prices_by_security.get(normalize_security_key(signal.security_key), []),
            key=lambda point: point.on,
        )
        if not series:
            continue

        entry_index = _first_price_after(series, signal.as_of_date)
        if entry_index is None:
            continue
        entry = series[entry_index]
        benchmark_entry = benchmark_prices.get(entry.on)
        if benchmark_entry is None:
            continue

        for horizon in horizons:
            exit_index = entry_index + horizon
            if exit_index >= len(series):
                continue
            exit_price = series[exit_index]
            benchmark_exit = benchmark_prices.get(exit_price.on)
            if benchmark_exit is None:
                continue

            stock_return = _return(entry.adj_close, exit_price.adj_close)
            benchmark_return = _return(benchmark_entry.adj_close, benchmark_exit.adj_close)
            if stock_return is None or benchmark_return is None:
                continue
            outcomes.append(
                SignalOutcome(
                    security_key=signal.security_key,
                    as_of_date=signal.as_of_date,
                    horizon_days=horizon,
                    benchmark_key=benchmark_key,
                    start_date=entry.on,
                    end_date=exit_price.on,
                    stock_return=stock_return,
                    benchmark_return=benchmark_return,
                    excess_return=stock_return - benchmark_return,
                    signal_score=signal.conviction_score,
                )
            )
    return outcomes


def summarize_performance(
    outcomes: list[SignalOutcome],
    *,
    bucket: str,
    horizon_days: int,
) -> PerformanceSummary:
    sample_size = len(outcomes)
    if not outcomes:
        return PerformanceSummary(
            bucket=bucket,
            horizon_days=horizon_days,
            sample_size=0,
            hit_rate=None,
            average_excess_return=None,
            median_excess_return=None,
            information_coefficient=None,
        )

    excess_returns = [outcome.excess_return for outcome in outcomes]
    hits = [value for value in excess_returns if value > 0]
    return PerformanceSummary(
        bucket=bucket,
        horizon_days=horizon_days,
        sample_size=sample_size,
        hit_rate=len(hits) / sample_size,
        average_excess_return=sum(excess_returns) / sample_size,
        median_excess_return=median(excess_returns),
        information_coefficient=spearman_rank_correlation(
            [outcome.signal_score for outcome in outcomes],
            excess_returns,
        ),
    )


def spearman_rank_correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_ranks = _ranks(left)
    right_ranks = _ranks(right)
    if len(set(left_ranks)) <= 1 or len(set(right_ranks)) <= 1:
        return None

    mean_left = sum(left_ranks) / len(left_ranks)
    mean_right = sum(right_ranks) / len(right_ranks)
    covariance = sum(
        (left_rank - mean_left) * (right_rank - mean_right)
        for left_rank, right_rank in zip(left_ranks, right_ranks, strict=True)
    )
    left_variance = sum((rank - mean_left) ** 2 for rank in left_ranks)
    right_variance = sum((rank - mean_right) ** 2 for rank in right_ranks)
    denominator = (left_variance * right_variance) ** 0.5
    if denominator == 0:
        return None
    return covariance / denominator


def benchmark_security_key(ticker: str) -> str:
    key = holding_key(ticker, ticker)
    if key is None:
        raise ValueError(f"Invalid benchmark ticker: {ticker}")
    return key


def _first_price_after(series: list[SecurityPrice], as_of_date: date) -> int | None:
    for index, price in enumerate(series):
        if price.on > as_of_date:
            return index
    return None


def _prices_by_date(series: list[SecurityPrice]) -> dict[date, SecurityPrice]:
    return {price.on: price for price in series}


def _return(start: float, end: float) -> float | None:
    if start <= 0:
        return None
    return (end / start) - 1


def _outcome_in_bucket(outcome: SignalOutcome, bucket: str) -> bool:
    match bucket:
        case "all":
            return True
        case "conviction_1":
            return outcome.signal_score == 1
        case "conviction_2_plus":
            return outcome.signal_score >= 2
        case "conviction_3_plus":
            return outcome.signal_score >= 3
        case _:
            return False


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[position][1]:
            end += 1
        average_rank = ((position + 1) + (end + 1)) / 2
        for offset in range(position, end + 1):
            ranks[indexed[offset][0]] = average_rank
        position = end + 1
    return ranks
