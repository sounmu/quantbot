from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class TRowePriceHoldingsProvider(CsvHoldingsProviderBase):
    _URLS = {
        "TCAF": (
            "https://www.troweprice.com/financial-intermediary/us/en/investments/"
            "etfs/capital-appreciation-equity-etf.html"
        )
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper().replace(".", "") == "T ROWE PRICE"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        url = self._URLS.get(ticker)
        if url is None:
            return []

        return self._html_to_holdings(ticker, self._decode_text(await self.download_bytes(url)))

    def parse_fixture(self, ticker: str, html_text: str) -> list[Holding]:
        return self._html_to_holdings(normalize_ticker(ticker), html_text)

    def _html_to_holdings(self, ticker: str, html_text: str) -> list[Holding]:
        full = self._find_full_holdings_payload(html_text)
        if full is None:
            return []

        as_of = self.parse_date(full.get("effectiveDate"))
        rows = full.get("holdings")
        if not isinstance(rows, list):
            return []

        holdings: list[Holding] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            holding_name = str(row.get("name") or "").strip()
            holding_ticker = self.clean_holding_ticker(
                row.get("tickerSymbol")
            ) or self.clean_holding_ticker(row.get("prioritizedIdentifier"))
            if self._is_excluded_row(holding_name, holding_ticker, row):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(row.get("percentageTotalNetAssets"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    security_id=self.clean_holding_ticker(row.get("prioritizedIdentifier"))
                    or self.clean_holding_ticker(row.get("cusip")),
                    shares=self.parse_number(row.get("shareQuantity")),
                    market_value=self.parse_number(row.get("marketValue")),
                    weight=weight,
                )
            )
        return holdings

    def _find_full_holdings_payload(self, html_text: str) -> dict[str, Any] | None:
        for match in re.finditer(r'data-component-object="([^"]*)"', html_text):
            try:
                payload = json.loads(unescape(match.group(1)))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            full = payload.get("full")
            if isinstance(full, dict) and isinstance(full.get("holdings"), list):
                return full
        return None

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        row: dict[str, Any],
    ) -> bool:
        text = " ".join(
            str(value).upper()
            for value in (
                holding_name,
                holding_ticker,
                row.get("investmentType"),
                row.get("assetType"),
            )
            if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "CURRENCY", "FUTURE", "FORWARD"))
