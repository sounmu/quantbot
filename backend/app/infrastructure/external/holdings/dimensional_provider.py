from __future__ import annotations

import re
from datetime import date
from typing import Any

import httpx

from app.config import get_settings
from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.base import with_backoff
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase

_BLOOMBERG_SUFFIX = re.compile(r"\s+[A-Z]{1,2}$")


class DimensionalHoldingsProvider(CsvHoldingsProviderBase):
    """Dimensional (DFA) actively-managed, fully-transparent US-equity ETFs.

    Daily holdings are published as a dated CSV at a public blob endpoint:
    ``https://tools-blob.dimensional.com/etf/{YYYYMMDD}/{TICKER}.csv``. The
    YYYYMMDD must be a valid trading date (non-trading days 404), so the latest
    published date is resolved from the public fund-center JSON before building
    the CSV URL. Tickers in the file are Bloomberg-style (``MCHP US``); the
    trailing country suffix is stripped. The CSV exposes CUSIP (``identifier``)
    and ISIN, so ``security_id`` is populated.
    """

    _BLOB_URL = "https://tools-blob.dimensional.com/etf/{date}/{ticker}.csv"
    _FUNDCENTER_URL = "https://etf.dimensional.com/public/v2/fundcenter"
    _SUPPORTED = {
        "DFAC",
        "DFUS",
        "DFUV",
        "DFAS",
        "DFAT",
        "DFAU",
        "DUHP",
        "DFSV",
        "DFLV",
        "DCOR",
        "DFSU",
        "DFVX",
        "DXUV",
        "DUSG",
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "DIMENSIONAL"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        if ticker not in self._SUPPORTED:
            return []

        as_of_compact = await self._latest_holdings_date()
        url = self._BLOB_URL.format(date=as_of_compact, ticker=ticker)
        rows = await self.download_csv(url)
        return self._rows_to_holdings(ticker, rows)

    def parse_fixture(self, ticker: str, csv_text: str) -> list[Holding]:
        return self._rows_to_holdings(normalize_ticker(ticker), self.parse_csv(csv_text))

    async def _latest_holdings_date(self) -> str:
        settings = get_settings()

        async def operation() -> str:
            async with httpx.AsyncClient(
                timeout=settings.holdings_http_timeout,
                headers={
                    "User-Agent": "quantbot/0.1 holdings tracker",
                    "x-selected-country": "US",
                },
            ) as client:
                response = await client.get(self._FUNDCENTER_URL)
                response.raise_for_status()
                payload = response.json()
            price_dates = payload.get("data", {}).get("priceDates") or []
            if not price_dates:
                raise ValueError("Dimensional fund-center returned no price dates")
            latest = str(price_dates[0].get("value") or "")
            compact = latest.replace("-", "")
            if not re.fullmatch(r"\d{8}", compact):
                raise ValueError(f"Unexpected Dimensional price date: {latest!r}")
            return compact

        return await with_backoff(operation)

    def _rows_to_holdings(self, ticker: str, rows: list[dict[str, str]]) -> list[Holding]:
        holdings: list[Holding] = []
        for row in rows:
            if normalize_ticker(row.get("etf_ticker") or ticker) != ticker:
                continue

            holding_name = str(row.get("description") or "").strip()
            holding_ticker = self._clean_dimensional_ticker(row.get("ticker"))
            security_id = self.clean_holding_ticker(
                row.get("identifier")
            ) or self.clean_holding_ticker(row.get("isin"))
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self._parse_fractional_weight(row.get("weight"))
            if weight is None:
                continue

            as_of = self._row_date(row)
            if as_of is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    security_id=security_id,
                    shares=self.parse_number(row.get("shares")),
                    market_value=self.parse_number(row.get("market_value")),
                    weight=weight,
                )
            )
        return holdings

    def _row_date(self, row: dict[str, Any]) -> date | None:
        raw = row.get("date")
        if not raw:
            return None
        try:
            return self.parse_date(raw)
        except ValueError:
            return None

    def _clean_dimensional_ticker(self, value: Any) -> str | None:
        ticker = self.clean_holding_ticker(value)
        if ticker is None:
            return None
        return _BLOOMBERG_SUFFIX.sub("", ticker).strip() or None

    def _parse_fractional_weight(self, value: Any) -> float | None:
        parsed = self.parse_number(value)
        if parsed is None:
            return None
        # Dimensional publishes weight as a fraction (0.000477915 == 0.0478%).
        return parsed * 100
