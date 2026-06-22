from __future__ import annotations

from datetime import date, timedelta

from app.domain.entities import Metric, PricePoint


class MetricService:
    def calculate(self, ticker: str, prices: list[PricePoint], *, aum: float | None = None) -> Metric | None:
        ordered = sorted(prices, key=lambda point: point.on)
        if not ordered:
            return None

        latest = ordered[-1]
        return Metric(
            ticker=ticker,
            as_of=latest.on,
            aum=aum,
            return_1m=self._return_since(ordered, latest.on - timedelta(days=31)),
            return_3m=self._return_since(ordered, latest.on - timedelta(days=93)),
            return_ytd=self._return_since(ordered, date(latest.on.year, 1, 1)),
            return_1y=self._return_since(ordered, latest.on - timedelta(days=366)),
        )

    def _return_since(self, prices: list[PricePoint], since: date) -> float | None:
        if len(prices) < 2:
            return None

        latest = prices[-1]
        baseline = next((point for point in prices if point.on >= since), prices[0])
        if baseline.close <= 0:
            return None
        return round(((latest.close / baseline.close) - 1) * 100, 4)

