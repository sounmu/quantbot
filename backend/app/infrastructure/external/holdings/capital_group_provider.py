from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class CapitalGroupHoldingsProvider(CsvHoldingsProviderBase):
    _BASE_URL = "https://www.capitalgroup.com/api/investments/investment-service/v1/etfs/"
    _URLS = {
        "CGGR": f"{_BASE_URL}CGGR/download/daily-holdings?audience=advisor",
        "CGDV": f"{_BASE_URL}CGDV/download/daily-holdings?audience=advisor",
        "CGUS": f"{_BASE_URL}CGUS/download/daily-holdings?audience=advisor",
        "CGCV": f"{_BASE_URL}CGCV/download/daily-holdings?audience=advisor",
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "CAPITAL GROUP"

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
            sheet="Daily Fund Holdings",
            header_contains=("Security Name", "Percent of Net Assets"),
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
            holding_name = str(row.get("security name") or "").strip()
            holding_ticker = self.clean_holding_ticker(
                row.get("ticker")
            ) or self.clean_holding_ticker(row.get("cusip"))
            asset_type = row.get("asset type")
            if self._is_excluded_row(holding_name, holding_ticker, asset_type):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self._parse_weight(row.get("percent of net assets"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    security_id=self.clean_holding_ticker(row.get("cusip")),
                    shares=self.parse_number(row.get("shares or principal amount")),
                    market_value=self.parse_number(row.get("market value")),
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
        raise ValueError("Could not find Capital Group holdings date in workbook metadata")

    def _parse_weight(self, value: Any) -> float | None:
        parsed = self.parse_number(value)
        if parsed is None:
            return None
        if isinstance(value, str) and "%" in value:
            return parsed
        if abs(parsed) <= 1:
            return parsed * 100
        return parsed

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        asset_type: Any,
    ) -> bool:
        text = " ".join(
            str(value).upper()
            for value in (holding_name, holding_ticker, asset_type)
            if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "MONEY MARKET", "CURRENCY"))
