from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class AvantisHoldingsProvider(CsvHoldingsProviderBase):
    _BASE_URL = "https://www.avantisinvestors.com/avantis-investments/"
    _URLS = {
        "AVUV": f"{_BASE_URL}avantis-us-small-cap-value-etf/",
        "AVDV": f"{_BASE_URL}avantis-international-small-cap-value-etf/",
        "AVUS": f"{_BASE_URL}avantis-us-equity-etf/",
        "AVLV": f"{_BASE_URL}avantis-us-large-cap-value-etf/",
        "AVLC": f"{_BASE_URL}avantis-us-large-cap-equity-etf/",
        "AVSC": f"{_BASE_URL}avantis-us-small-cap-equity-etf/",
        "AVMV": f"{_BASE_URL}avantis-us-mid-cap-value-etf/",
        "AVMC": f"{_BASE_URL}avantis-us-mid-cap-equity-etf/",
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "AVANTIS"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        url = self._URLS.get(ticker)
        if url is None:
            return []

        return self._html_to_holdings(ticker, self._decode_text(await self.download_bytes(url)))

    def parse_fixture(self, ticker: str, html_text: str) -> list[Holding]:
        return self._html_to_holdings(normalize_ticker(ticker), html_text)

    def _html_to_holdings(self, ticker: str, html_text: str) -> list[Holding]:
        rows = self._find_etf_holdings_payload(html_text)
        if not rows:
            return []

        as_of = self._date_from_html(html_text)
        holdings: list[Holding] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            holding_name = str(row.get("name") or "").strip()
            holding_ticker = self.clean_holding_ticker(
                row.get("ticker")
            ) or self.clean_holding_ticker(row.get("cusip"))
            if self._is_excluded_row(holding_name, holding_ticker, row):
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
                    security_id=self.clean_holding_ticker(row.get("cusip"))
                    or self.clean_holding_ticker(row.get("isin")),
                    shares=self.parse_number(row.get("shareQuantity")),
                    market_value=self.parse_number(row.get("baseMarketValue")),
                    weight=weight,
                )
            )
        return self._merge_duplicate_rows(holdings)

    def _find_etf_holdings_payload(self, html_text: str) -> list[dict[str, Any]]:
        array_text = self._extract_js_array(html_text, "etfHoldings:[")
        if array_text is None:
            return []

        json_text = re.sub(
            r"([\{,])([A-Za-z_$][A-Za-z0-9_$]*):",
            r'\1"\2":',
            array_text,
        )
        payload = json.loads(json_text)
        return payload if isinstance(payload, list) else []

    def _extract_js_array(self, html_text: str, marker: str) -> str | None:
        marker_start = html_text.find(marker)
        if marker_start < 0:
            return None
        array_start = html_text.find("[", marker_start)
        if array_start < 0:
            return None

        depth = 0
        in_string = False
        escape = False
        for index, char in enumerate(html_text[array_start:], start=array_start):
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return html_text[array_start : index + 1]
        return None

    def _date_from_html(self, html_text: str) -> date:
        for key in ("etfHoldingsAsOfDate", "topHoldingsAsOfDate", "navAsOfDate"):
            match = re.search(rf'{key}:"([^"]+)"', html_text)
            if match:
                return self.parse_date(match.group(1))
        raise ValueError("Could not find Avantis holdings date in page payload")

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        row: dict[str, Any],
    ) -> bool:
        security_type = str(row.get("securityType") or "").upper()
        cusip = str(row.get("cusip") or "").upper()
        normalized_name = " ".join(holding_name.upper().replace("/", " ").split())
        if "SWEEP" in security_type or "CURRENCY" in security_type:
            return True
        if not security_type and (cusip.startswith("999") or holding_ticker is None):
            return True
        return normalized_name in {"US DOLLAR", "CASH", "CASH EQUIVALENTS"}

    def _merge_duplicate_rows(self, holdings: list[Holding]) -> list[Holding]:
        merged: dict[tuple[str | None, str], Holding] = {}
        order: list[tuple[str | None, str]] = []
        for holding in holdings:
            key = (holding.holding_ticker, holding.holding_name)
            existing = merged.get(key)
            if existing is None:
                merged[key] = holding
                order.append(key)
                continue

            existing.weight += holding.weight
            existing.shares = self._sum_optional(existing.shares, holding.shares)
            existing.market_value = self._sum_optional(existing.market_value, holding.market_value)
        return [merged[key] for key in order]

    def _sum_optional(self, left: float | None, right: float | None) -> float | None:
        if left is None:
            return right
        if right is None:
            return left
        return left + right
