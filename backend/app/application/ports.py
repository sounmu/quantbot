from __future__ import annotations

from typing import Protocol

from app.domain.entities import Etf, Holding, PricePoint


class HoldingsProvider(Protocol):
    def supports(self, issuer: str) -> bool: ...

    async def fetch_holdings(self, etf: Etf) -> list[Holding]: ...


class MarketDataProvider(Protocol):
    async def fetch_prices(self, ticker: str, *, lookback_days: int) -> list[PricePoint]: ...

    async def fetch_profile(self, ticker: str) -> Etf | None: ...
