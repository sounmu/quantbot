from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class SpdrHoldingsProvider(CsvHoldingsProviderBase):
    _URLS = {
        "TOTL": "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-totl.xlsx"
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "STATE STREET"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        url = self._URLS.get(ticker)
        if url is None:
            return []

        return self._xlsx_to_holdings(ticker, await self.download_bytes(url))

    def parse_fixture(self, ticker: str, xlsx_bytes: bytes) -> list[Holding]:
        return self._xlsx_to_holdings(normalize_ticker(ticker), xlsx_bytes)

    def _xlsx_to_holdings(self, ticker: str, xlsx_bytes: bytes) -> list[Holding]:
        metadata, rows = self.parse_xlsx_with_preamble(
            xlsx_bytes,
            sheet="holdings",
            header_contains=("Name", "Weight"),
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
            raw_identifier = row.get("identifier")
            holding_ticker = self.clean_holding_ticker(raw_identifier) or self.clean_holding_ticker(
                row.get("isin")
            )
            if self._is_excluded_row(holding_name, raw_identifier):
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
                    shares=self.parse_number(row.get("par value")),
                    market_value=self.parse_number(row.get("market value")),
                    weight=weight,
                )
            )
        return holdings

    def _date_from_metadata(self, metadata: dict[str, str]) -> date:
        for key in ("holdings", "as of", "date"):
            value = metadata.get(key)
            if value:
                return self.parse_date(value)
        for value in metadata.values():
            try:
                return self.parse_date(value)
            except ValueError:
                continue
        raise ValueError("Could not find SPDR holdings date in workbook metadata")

    def _is_excluded_row(self, holding_name: str, raw_identifier: Any) -> bool:
        text = " ".join(
            str(value).upper() for value in (holding_name, raw_identifier) if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "US DOLLAR", "US DOLLARS", "USDOLLAR"))
