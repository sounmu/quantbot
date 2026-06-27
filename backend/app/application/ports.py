from __future__ import annotations

from typing import Protocol

from app.domain.entities import Etf, EtfProfile, Holding, PricePoint, Security, SecurityPrice


class HoldingsProvider(Protocol):
    def supports(self, issuer: str) -> bool: ...

    async def fetch_holdings(self, etf: Etf) -> list[Holding]: ...


class MarketDataProvider(Protocol):
    async def fetch_prices(self, ticker: str, *, lookback_days: int) -> list[PricePoint]: ...

    async def fetch_profile(self, ticker: str) -> EtfProfile | None: ...

    async def fetch_security_prices(
        self,
        security: Security,
        *,
        lookback_days: int,
    ) -> list[SecurityPrice]: ...
