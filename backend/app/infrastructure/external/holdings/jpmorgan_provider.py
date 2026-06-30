from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase

_DATE_PATTERN = re.compile(r"(\d{1,2}/\d{1,2}/\d{2,4})")


class JPMorganHoldingsProvider(CsvHoldingsProviderBase):
    """JPMorgan Asset Management fully-transparent active ETFs.

    Daily holdings are published as an XLSX from a single CUSIP-parameterized
    handler. JEPI/JEPQ hold equities plus equity-linked notes (ELNs); only the
    physically-held equity sleeve carries real share counts, so ELN and currency
    rows are filtered out. There is no CUSIP/ISIN column in the export, so the
    ``holding_key`` falls through to the ticker (same identity policy as ARK).
    """

    _BASE_URL = "https://am.jpmorgan.com/FundsMarketingHandler/excel"
    _CUSIPS = {
        "JEPI": "46641Q332",
        "JEPQ": "46654Q203",
        "JGRO": "46654Q609",
        "JAVA": "46641Q167",
        "JTEK": "46654Q732",
        "JUSA": "46654Q617",
        "JPSV": "46654Q708",
    }
    _HEADER = ("Ticker", "Security Description", "Shares/Par")
    _EXCLUDED_SECURITY_TYPES = ("EQUITY LINKED NOTE", "CURRENC", "CASH", "MONEY MARKET")

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "JPMORGAN"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        cusip = self._CUSIPS.get(ticker)
        if cusip is None:
            return []

        url = (
            f"{self._BASE_URL}?type=dailyETFHoldings&cusip={cusip}"
            "&country=us&role=adv&locale=en-US"
        )
        return self._xlsx_to_holdings(ticker, await self.download_bytes(url))

    def parse_fixture(self, ticker: str, xlsx_bytes: bytes) -> list[Holding]:
        return self._xlsx_to_holdings(normalize_ticker(ticker), xlsx_bytes)

    def _xlsx_to_holdings(self, ticker: str, xlsx_bytes: bytes) -> list[Holding]:
        metadata, rows = self.parse_xlsx_with_preamble(
            xlsx_bytes,
            header_contains=self._HEADER,
        )
        as_of = self._date_from_metadata(metadata)
        return self._rows_to_holdings(ticker, rows, as_of)

    def _rows_to_holdings(
        self,
        ticker: str,
        rows: list[dict[str, Any]],
        as_of: date,
    ) -> list[Holding]:
        holdings: list[Holding] = []
        for row in rows:
            holding_name = str(row.get("security description") or "").strip()
            holding_ticker = self.clean_holding_ticker(row.get("ticker"))
            security_type = row.get("security type")
            if self._is_excluded_row(holding_name, holding_ticker, security_type):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(row.get("% of net assets"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    shares=self.parse_number(row.get("shares/par")),
                    market_value=self.parse_number(row.get("market value (usd)")),
                    weight=weight,
                )
            )
        return holdings

    def _date_from_metadata(self, metadata: dict[str, str]) -> date:
        for value in metadata.values():
            match = _DATE_PATTERN.search(str(value))
            if match:
                try:
                    return self.parse_date(match.group(1))
                except ValueError:
                    continue
        raise ValueError("Could not find JPMorgan holdings date in workbook preamble")

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        security_type: Any,
    ) -> bool:
        normalized_type = str(security_type or "").upper()
        if any(token in normalized_type for token in self._EXCLUDED_SECURITY_TYPES):
            return True
        text = " ".join(
            str(value).upper()
            for value in (holding_name, holding_ticker)
            if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "MONEY MARKET"))
