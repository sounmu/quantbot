from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class VirtusHoldingsProvider(CsvHoldingsProviderBase):
    _URLS = {
        "PFFA": "https://www.virtus.com/assets/files/1xx/positions_pffa.xls",
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "VIRTUS"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        url = self._URLS.get(ticker)
        if url is None:
            return []

        return self._xls_to_holdings(ticker, await self.download_bytes(url))

    def parse_fixture(self, ticker: str, xls_bytes: bytes) -> list[Holding]:
        return self._xls_to_holdings(normalize_ticker(ticker), xls_bytes)

    def _xls_to_holdings(self, ticker: str, xls_bytes: bytes) -> list[Holding]:
        metadata, rows = self.parse_xls_with_preamble(
            xls_bytes,
            header_contains=("Name", "Ticker", "Quantity", "Weight"),
        )
        return self._rows_to_holdings(ticker, rows, self._date_from_metadata(metadata))

    def _rows_to_holdings(
        self,
        ticker: str,
        rows: list[dict[str, Any]],
        as_of: date,
    ) -> list[Holding]:
        holdings: list[Holding] = []
        for row in rows:
            holding_name = str(row.get("name") or "").strip()
            holding_ticker = self.clean_holding_ticker(
                row.get("ticker")
            ) or self.clean_holding_ticker(row.get("security id"))
            if self._is_excluded_row(holding_name, holding_ticker, row.get("security type")):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(row.get("weight"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    shares=self.parse_number(row.get("quantity")),
                    market_value=self.parse_number(row.get("(local)")),
                    weight=weight,
                )
            )
        return holdings

    def _date_from_metadata(self, metadata: dict[str, str]) -> date:
        for value in metadata.values():
            try:
                return self.parse_date(value)
            except ValueError:
                continue
        raise ValueError("Could not find Virtus holdings date in workbook metadata")

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        security_type: Any,
    ) -> bool:
        text = " ".join(
            str(value).upper()
            for value in (holding_name, holding_ticker, security_type)
            if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "CURRENCY", "SWEEP"))
