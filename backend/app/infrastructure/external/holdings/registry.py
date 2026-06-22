from __future__ import annotations

from app.application.ports import HoldingsProvider
from app.domain.entities import Etf
from app.infrastructure.external.holdings.ark_provider import ArkHoldingsProvider


class HoldingsProviderRegistry:
    def __init__(self, providers: list[HoldingsProvider] | None = None) -> None:
        self._providers = providers or [ArkHoldingsProvider()]

    def provider_for(self, etf: Etf) -> HoldingsProvider | None:
        if not etf.discloses_daily:
            return None
        return next((provider for provider in self._providers if provider.supports(etf.issuer)), None)

