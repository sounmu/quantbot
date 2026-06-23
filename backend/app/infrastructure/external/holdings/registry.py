from __future__ import annotations

from app.application.ports import HoldingsProvider
from app.domain.entities import Etf
from app.infrastructure.external.holdings.ark_provider import ArkHoldingsProvider
from app.infrastructure.external.holdings.avantis_provider import AvantisHoldingsProvider
from app.infrastructure.external.holdings.capital_group_provider import CapitalGroupHoldingsProvider
from app.infrastructure.external.holdings.ishares_provider import ISharesHoldingsProvider
from app.infrastructure.external.holdings.spdr_provider import SpdrHoldingsProvider
from app.infrastructure.external.holdings.trowe_price_provider import TRowePriceHoldingsProvider
from app.infrastructure.external.holdings.virtus_provider import VirtusHoldingsProvider


class HoldingsProviderRegistry:
    def __init__(self, providers: list[HoldingsProvider] | None = None) -> None:
        self._providers = providers or [
            ArkHoldingsProvider(),
            ISharesHoldingsProvider(),
            SpdrHoldingsProvider(),
            CapitalGroupHoldingsProvider(),
            TRowePriceHoldingsProvider(),
            AvantisHoldingsProvider(),
            VirtusHoldingsProvider(),
        ]

    def provider_for(self, etf: Etf) -> HoldingsProvider | None:
        if not etf.discloses_daily:
            return None
        return next(
            (provider for provider in self._providers if provider.supports(etf.issuer)), None
        )
