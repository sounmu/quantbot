from __future__ import annotations

import re
from datetime import UTC, date, datetime

from app.application.services.universe_service import unsupported_analysis_reason
from app.domain.entities import Holding, Security
from app.domain.repositories import EtfRepository, HoldingRepository, SecurityRepository
from app.domain.value_objects import holding_key, normalize_security_key, normalize_ticker


_PRICE_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}(?:-[A-Z])?$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
_CURRENCY_PLACEHOLDER_PATTERN = re.compile(r"^[A-Z]{3}9{6}$")
_NON_US_CURRENCY_CODES = {
    "AUD",
    "BRL",
    "CAD",
    "CHF",
    "CNH",
    "CNY",
    "DKK",
    "EUR",
    "GBP",
    "HKD",
    "IDR",
    "ILS",
    "INR",
    "JPY",
    "KRW",
    "MXN",
    "MYR",
    "NOK",
    "NZD",
    "PHP",
    "PLN",
    "SEK",
    "SGD",
    "THB",
    "TRY",
    "TWD",
    "ZAR",
}
_UNSUPPORTED_SECURITY_NAME_TOKENS = {
    "BOND",
    "BONDS",
    "ETF",
    "FORWARD",
    "FUND",
    "FUTURE",
    "NOTE",
    "NOTES",
    "OPTION",
    "PREFERENCE",
    "PREFERRED",
    "RIGHT",
    "RIGHTS",
    "STAKING",
    "WARRANT",
    "WARRANTS",
}
_SECURITY_PAGE_SIZE = 500


class UnderlyingSecurityService:
    def __init__(
        self,
        *,
        etfs: EtfRepository,
        holdings: HoldingRepository,
        securities: SecurityRepository,
    ) -> None:
        self._etfs = etfs
        self._holdings = holdings
        self._securities = securities

    async def refresh_priceable_security_master(
        self,
        *,
        benchmark_ticker: str,
    ) -> tuple[list[Security], int]:
        securities = await self.discover_priceable_securities(benchmark_ticker=benchmark_ticker)
        written = await self._securities.upsert_many(securities)
        return securities, written

    async def discover_priceable_securities(self, *, benchmark_ticker: str) -> list[Security]:
        discovered: list[Security] = []
        today = datetime.now(UTC).date()
        benchmark = security_from_benchmark(benchmark_ticker, today=today)
        if benchmark is not None:
            discovered.append(benchmark)

        page = 1
        while True:
            batch, total = await self._etfs.list(page=page, page_size=_SECURITY_PAGE_SIZE)
            for etf in batch:
                if not etf.in_signal_universe or unsupported_analysis_reason(etf) is not None:
                    continue
                for holding in await self._holdings.latest(etf.ticker):
                    security = security_from_holding(holding)
                    if security is not None:
                        discovered.append(security)
            if page * _SECURITY_PAGE_SIZE >= total or not batch:
                break
            page += 1

        return _dedupe_securities(discovered)


def security_from_benchmark(ticker: str, *, today: date) -> Security | None:
    price_ticker = _normalize_price_ticker(ticker)
    if price_ticker is None:
        return None
    key = holding_key(price_ticker, price_ticker)
    if key is None:
        return None
    return Security(
        security_key=key,
        ticker=price_ticker,
        name=f"{price_ticker} benchmark",
        first_seen=today,
        is_priceable=True,
    )


def security_from_holding(holding: Holding) -> Security | None:
    price_ticker = price_ticker_for_holding(holding)
    if price_ticker is None:
        return None

    key = holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
    if key is None:
        return None
    return Security(
        security_key=key,
        ticker=price_ticker,
        name=holding.holding_name,
        first_seen=holding.as_of_date,
        is_priceable=True,
    )


def price_ticker_for_holding(holding: Holding) -> str | None:
    ticker = _normalize_price_ticker(holding.holding_ticker)
    if ticker is None:
        return None

    security_id = (holding.security_id or "").strip().upper()
    if _is_currency_placeholder(security_id) or security_id.startswith("999"):
        return None
    if _ISIN_PATTERN.fullmatch(security_id) and not security_id.startswith("US"):
        return None
    if _has_explicit_non_us_currency(holding.holding_name):
        return None
    if _has_unsupported_security_name(holding.holding_name):
        return None
    return ticker


def incremental_price_lookback_days(
    latest: date | None,
    *,
    requested_lookback_days: int,
    overlap_days: int,
    today: date | None = None,
) -> int | None:
    requested = max(requested_lookback_days, 1)
    if latest is None:
        return requested

    current_date = today or datetime.now(UTC).date()
    days_since_latest = (current_date - latest).days
    if days_since_latest <= 0:
        return None
    return min(requested, max(days_since_latest + max(overlap_days, 0), 1))


def _normalize_price_ticker(ticker: str | None) -> str | None:
    if ticker is None:
        return None
    raw = ticker.strip()
    if not raw or any(char.isspace() for char in raw) or "." in raw:
        return None

    normalized = normalize_ticker(raw).replace("/", "-")
    if _is_currency_placeholder(normalized):
        return None
    if any(char.isdigit() for char in normalized):
        return None
    if not _PRICE_TICKER_PATTERN.fullmatch(normalized):
        return None
    return normalized


def _is_currency_placeholder(value: str) -> bool:
    return bool(_CURRENCY_PLACEHOLDER_PATTERN.fullmatch(value))


def _has_explicit_non_us_currency(name: str) -> bool:
    tokens = set(re.sub(r"[^A-Z0-9]+", " ", name.upper()).split())
    return bool(tokens & _NON_US_CURRENCY_CODES)


def _has_unsupported_security_name(name: str) -> bool:
    tokens = set(re.sub(r"[^A-Z0-9]+", " ", name.upper()).split())
    return bool(tokens & _UNSUPPORTED_SECURITY_NAME_TOKENS)


def _dedupe_securities(securities: list[Security]) -> list[Security]:
    by_key: dict[str, Security] = {}
    order: list[str] = []
    for security in securities:
        key = normalize_security_key(security.security_key)
        existing = by_key.get(key)
        normalized = Security(
            security_key=key,
            ticker=normalize_ticker(security.ticker),
            name=security.name,
            first_seen=security.first_seen,
            is_priceable=security.is_priceable,
        )
        if existing is None:
            by_key[key] = normalized
            order.append(key)
            continue
        if normalized.first_seen < existing.first_seen:
            existing.first_seen = normalized.first_seen
        existing.ticker = normalized.ticker
        existing.name = normalized.name or existing.name
        existing.is_priceable = existing.is_priceable or normalized.is_priceable
    return [by_key[key] for key in order]
