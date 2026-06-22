from __future__ import annotations

import asyncio
import math
from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding, PricePoint
from app.domain.value_objects import normalize_ticker
from app.infrastructure.external.base import with_backoff


class YFinanceMarketDataProvider:
    async def fetch_prices(self, ticker: str, *, lookback_days: int) -> list[PricePoint]:
        normalized = normalize_ticker(ticker)

        async def operation() -> list[PricePoint]:
            return await asyncio.to_thread(self._fetch_prices_sync, normalized, lookback_days)

        return await with_backoff(operation)

    async def fetch_profile(self, ticker: str) -> Etf | None:
        return None

    async def fetch_holdings(self, ticker: str) -> list[Holding]:
        return []

    def _fetch_prices_sync(self, ticker: str, lookback_days: int) -> list[PricePoint]:
        import yfinance as yf

        frame = yf.Ticker(ticker).history(
            period=f"{max(lookback_days, 1)}d",
            interval="1d",
            auto_adjust=False,
        )
        if frame.empty:
            return []

        points: list[PricePoint] = []
        for index, row in frame.iterrows():
            close = self._float_or_none(row.get("Close"))
            if close is None:
                continue
            points.append(
                PricePoint(
                    ticker=ticker,
                    on=self._date_from_index(index),
                    open=self._float_or_none(row.get("Open")),
                    high=self._float_or_none(row.get("High")),
                    low=self._float_or_none(row.get("Low")),
                    close=close,
                    volume=self._int_or_none(row.get("Volume")),
                )
            )
        return points

    def _date_from_index(self, value: Any) -> date:
        if hasattr(value, "date"):
            return value.date()
        return date.fromisoformat(str(value)[:10])

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number):
            return None
        return number

    def _int_or_none(self, value: Any) -> int | None:
        number = self._float_or_none(value)
        return int(number) if number is not None else None

