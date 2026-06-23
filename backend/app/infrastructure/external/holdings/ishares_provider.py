from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


class ISharesHoldingsProvider(CsvHoldingsProviderBase):
    _URLS = {
        "DYNF": (
            "https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v2/"
            "get-product-data?appType=PRODUCT_PAGE&appSubType=ISHARES&targetSite=us-ishares"
            "&locale=en_US&portfolioId=307283&component=holdings&userType=individual"
            "&excludeContent=true&includeConfig=true"
        )
    }

    def supports(self, issuer: str) -> bool:
        return issuer.strip().upper() == "BLACKROCK"

    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ticker = normalize_ticker(etf.ticker)
        url = self._URLS.get(ticker)
        if url is None:
            return []

        data = await self.download_json(url)
        if not isinstance(data, dict):
            return []
        return self._json_to_holdings(ticker, data)

    def parse_fixture(self, ticker: str, csv_text: str) -> list[Holding]:
        metadata, rows = self.parse_csv_with_preamble(
            csv_text,
            header_contains=("Ticker", "Name", "Weight (%)"),
        )
        return self._rows_to_holdings(normalize_ticker(ticker), rows, self._date_from_metadata(metadata))

    def parse_json_fixture(self, ticker: str, data: dict[str, Any]) -> list[Holding]:
        return self._json_to_holdings(normalize_ticker(ticker), data)

    def _json_to_holdings(self, ticker: str, data: dict[str, Any]) -> list[Holding]:
        data_points = (
            data.get("componentsByNameMap", {})
            .get("holdings", {})
            .get("containersByNameMap", {})
            .get("all", {})
            .get("dataPointsByNameMap", {})
        )
        if not isinstance(data_points, dict):
            return []

        as_of = self._date_from_data_points(data_points)
        tickers = self._data_point_values(data_points, "ticker")
        names = self._data_point_values(data_points, "issueName")
        shares = self._data_point_values(data_points, "unitsHeld")
        market_values = self._data_point_values(data_points, "marketValue")
        weights = self._data_point_values(data_points, "holdingPercent")
        asset_classes = self._data_point_values(data_points, "assetClass")

        holdings: list[Holding] = []
        for index in range(max(len(names), len(tickers), len(weights))):
            holding_name = str(self._at(names, index) or "").strip()
            holding_ticker = self.clean_holding_ticker(self._at(tickers, index))
            asset_class = self._at(asset_classes, index)
            if self._is_excluded_row(holding_name, holding_ticker, asset_class):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(self._at(weights, index))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    shares=self.parse_number(self._at(shares, index)),
                    market_value=self.parse_number(self._at(market_values, index)),
                    weight=weight,
                )
            )
        return holdings

    def _rows_to_holdings(
        self,
        ticker: str,
        rows: list[dict[str, Any]],
        as_of: date,
    ) -> list[Holding]:
        holdings: list[Holding] = []
        for row in rows:
            holding_name = str(self._first(row, "name", "issuer name", "security name") or "").strip()
            holding_ticker = self.clean_holding_ticker(self._first(row, "ticker", "issuer ticker"))
            asset_class = self._first(row, "asset class")
            if self._is_excluded_row(holding_name, holding_ticker, asset_class):
                continue
            if holding_key(holding_ticker, holding_name) is None:
                continue

            weight = self.parse_number(self._first(row, "weight (%)", "weight"))
            if weight is None:
                continue

            holdings.append(
                Holding(
                    ticker=ticker,
                    as_of_date=as_of,
                    holding_name=holding_name,
                    holding_ticker=holding_ticker,
                    shares=self.parse_number(self._first(row, "shares", "quantity", "nominal")),
                    market_value=self.parse_number(self._first(row, "market value")),
                    weight=weight,
                )
            )
        return holdings

    def _date_from_metadata(self, metadata: dict[str, str]) -> date:
        for key in ("fund holdings as of", "holdings as of", "as of", "date"):
            value = metadata.get(key)
            if value:
                return self.parse_date(value)
        for key, value in metadata.items():
            for candidate in (value, key):
                try:
                    return self.parse_date(candidate)
                except ValueError:
                    continue
        raise ValueError("Could not find iShares holdings date in preamble")

    def _date_from_data_points(self, data_points: dict[str, Any]) -> date:
        point = data_points.get("asOfDate") or {}
        if isinstance(point, dict):
            return self.parse_date(point.get("formattedValue") or point.get("value"))
        return self.parse_date(point)

    def _data_point_values(self, data_points: dict[str, Any], key: str) -> list[Any]:
        point = data_points.get(key)
        if not isinstance(point, dict):
            return []
        value = point.get("value")
        if isinstance(value, list):
            return value
        formatted = point.get("formattedValue")
        return formatted if isinstance(formatted, list) else []

    def _first(self, row: dict[str, Any], *keys: str) -> Any:
        return next((row[key] for key in keys if row.get(key) not in (None, "")), None)

    def _at(self, values: list[Any], index: int) -> Any:
        return values[index] if index < len(values) else None

    def _is_excluded_row(
        self,
        holding_name: str,
        holding_ticker: str | None,
        asset_class: Any,
    ) -> bool:
        text = " ".join(
            str(value).upper()
            for value in (holding_name, holding_ticker, asset_class)
            if value not in (None, "")
        )
        return any(token in text for token in ("CASH", "DERIVATIVE", "FORWARD", "FUTURE", "FX "))
