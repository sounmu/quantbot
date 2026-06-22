from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Any

import httpx

from app.config import get_settings
from app.infrastructure.external.base import with_backoff


class CsvHoldingsProviderBase:
    async def download_csv(self, url: str) -> list[dict[str, str]]:
        settings = get_settings()

        async def operation() -> list[dict[str, str]]:
            async with httpx.AsyncClient(
                timeout=settings.holdings_http_timeout,
                headers={"User-Agent": "quantbot/0.1 holdings tracker"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self.parse_csv(response.text)

        return await with_backoff(operation)

    def parse_csv(self, text: str) -> list[dict[str, str]]:
        return [
            {self.normalize_header(key): value for key, value in row.items() if key is not None}
            for row in csv.DictReader(StringIO(text))
        ]

    def normalize_header(self, value: str) -> str:
        return value.strip().lower()

    def parse_date(self, value: str) -> date:
        clean = value.strip()
        for pattern in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(clean, pattern).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported date value: {value}")

    def parse_number(self, value: Any) -> float | None:
        if value is None:
            return None
        clean = str(value).strip()
        if not clean or clean in {"--", "-", "N/A", "nan"}:
            return None
        clean = clean.replace("$", "").replace(",", "").replace("%", "")
        clean = clean.replace("(", "-").replace(")", "")
        try:
            return float(clean)
        except ValueError:
            return None

