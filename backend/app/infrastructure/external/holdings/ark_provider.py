from __future__ import annotations

from urllib.parse import quote

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class ArkHoldingsProvider(CsvHoldingsProviderBase):
    _BASE_URL = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/"
    _SLUGS = {
        "ARKK": "ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
        "ARKG": "ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
        "ARKW": "ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
        "ARKF": "ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
        "ARKX": "ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv",
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "ARK"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        slug = self._SLUGS.get(ticker)
        if slug is None:
            return []

        rows = await self.download_csv(self._BASE_URL + quote(slug, safe="_-."))
        return self._rows_to_holdings(ticker, rows)

    def parse_fixture(self, ticker: str, csv_text: str) -> list[Holding]:
        return self._rows_to_holdings(normalize_ticker(ticker), self.parse_csv(csv_text))

    def _rows_to_holdings(self, ticker: str, rows: list[dict[str, str]]) -> list[Holding]:
        holdings: list[Holding] = []
        for row in rows:
            if not row.get("fund") or not row.get("date"):
                continue
            if normalize_ticker(row.get("fund") or ticker) != ticker:
                continue

            holding_name = (row.get("company") or "").strip()
            holding_ticker = self._clean_holding_ticker(row.get("ticker"))
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(row.get("weight (%)"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=self.parse_date(row["date"]),
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    shares=self.parse_number(row.get("shares")),
                    market_value=self.parse_number(row.get("market value ($)")),
                    weight=weight,
                )
            )
        return holdings

    def _clean_holding_ticker(self, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip().upper()
        if clean in {"", "--", "-"}:
            return None
        return clean
