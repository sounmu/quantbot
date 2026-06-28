from __future__ import annotations

import asyncio
import math
import warnings
from datetime import UTC, date, datetime
from typing import Any

from app.domain.entities import EtfProfile, Holding, PricePoint, Security, SecurityPrice
from app.domain.value_objects import normalize_ticker
from app.infrastructure.external.base import with_backoff


class YFinanceMarketDataProvider:
    async def fetch_prices(self, ticker: str, *, lookback_days: int) -> list[PricePoint]:
        normalized = normalize_ticker(ticker)

        async def operation() -> list[PricePoint]:
            return await asyncio.to_thread(self._fetch_prices_sync, normalized, lookback_days)

        return await with_backoff(operation)

    async def fetch_profile(self, ticker: str) -> EtfProfile | None:
        normalized = normalize_ticker(ticker)

        async def operation() -> EtfProfile | None:
            return await asyncio.to_thread(self._fetch_profile_sync, normalized)

        return await with_backoff(operation)

    async def fetch_security_prices(
        self,
        security: Security,
        *,
        lookback_days: int,
    ) -> list[SecurityPrice]:
        async def operation() -> list[SecurityPrice]:
            return await asyncio.to_thread(self._fetch_security_prices_sync, security, lookback_days)

        return await with_backoff(operation)

    async def fetch_holdings(self, ticker: str) -> list[Holding]:
        return []

    def _fetch_prices_sync(self, ticker: str, lookback_days: int) -> list[PricePoint]:
        import yfinance as yf
        from yfinance.exceptions import YFPricesMissingError, YFTickerMissingError, YFTzMissingError

        try:
            frame = self._history(yf.Ticker(ticker), lookback_days)
        except (YFPricesMissingError, YFTickerMissingError, YFTzMissingError):
            return []
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

    def _fetch_security_prices_sync(
        self,
        security: Security,
        lookback_days: int,
    ) -> list[SecurityPrice]:
        import yfinance as yf
        from yfinance.exceptions import YFPricesMissingError, YFTickerMissingError, YFTzMissingError

        try:
            frame = self._history(yf.Ticker(security.ticker), lookback_days)
        except (YFPricesMissingError, YFTickerMissingError, YFTzMissingError):
            return []
        if frame.empty:
            return []

        points: list[SecurityPrice] = []
        for index, row in frame.iterrows():
            close = self._float_or_none(row.get("Close"))
            adj_close = self._float_or_none(row.get("Adj Close")) or close
            if close is None or adj_close is None:
                continue
            points.append(
                SecurityPrice(
                    security_key=security.security_key,
                    on=self._date_from_index(index),
                    close=close,
                    adj_close=adj_close,
                    volume=self._int_or_none(row.get("Volume")),
                )
            )
        return points

    def _fetch_profile_sync(self, ticker: str) -> EtfProfile | None:
        import yfinance as yf

        info = yf.Ticker(ticker).info
        exchange = self._string_or_none(info.get("fullExchangeName")) or self._string_or_none(
            info.get("exchange")
        )
        aum = self._float_or_none(info.get("totalAssets"))
        if exchange is None and aum is None:
            return None
        return EtfProfile(
            ticker=ticker,
            as_of=datetime.now(UTC).date(),
            exchange=exchange,
            aum=aum,
        )

    def _history(self, ticker: Any, lookback_days: int) -> Any:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="'raise_errors' deprecated.*",
                category=DeprecationWarning,
            )
            return ticker.history(
                period=f"{max(lookback_days, 1)}d",
                interval="1d",
                auto_adjust=False,
                raise_errors=True,
            )

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

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
