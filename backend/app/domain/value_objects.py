from __future__ import annotations

import re


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def normalize_security_key(security_key: str) -> str:
    return security_key.strip().upper()


class ChangeType:
    NEW = "NEW"
    EXIT = "EXIT"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    UNCHANGED = "UNCHANGED"


class SignalDirection:
    BUY = "BUY"
    SELL = "SELL"


_CASH_TOKENS = {"", "--", "-", "CASH", "USD", "US DOLLAR", "DOLLAR", "MONEYMARKET"}
_CASH_NAME_TOKENS = {"CASH", "CASHEQUIVALENTS", "CASHANDEQUIVALENTS", "USD", "USDOLLAR"}
_CURRENCY_CODES = {
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
    "USD",
    "ZAR",
}
_CURRENCY_PLACEHOLDER_PATTERN = re.compile(r"^[A-Z]{3}9{6}$")
_CURRENCY_NAME_MARKERS = {"CURRENCY", "FORWARD", "FX", "SPOT"}


def holding_key(
    holding_ticker: str | None,
    holding_name: str,
    security_id: str | None = None,
) -> str | None:
    # Prefer a globally-unique security identifier (CUSIP/ISIN/SEDOL) when available.
    # Local exchange tickers are not globally unique (e.g. "DRX" maps to both DRAX GROUP
    # and ADF GROUP across exchanges), so ticker-only keys collide for international ETFs.
    if security_id:
        normalized_id = security_id.strip().upper()
        if (
            normalized_id
            and not _is_cash_like_token(normalized_id)
            and not normalized_id.startswith("999")
        ):
            return f"ID:{normalized_id}"

    if holding_ticker and not _is_cash_like_token(holding_ticker):
        return holding_ticker.strip().upper()

    normalized_name = re.sub(r"[^A-Z0-9]", "", holding_name.upper())
    if _is_cash_like_name(holding_name, normalized_name):
        return None
    return f"NAME:{normalized_name}"


def _is_cash_like_token(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().upper()
    return normalized in _CASH_TOKENS or bool(_CURRENCY_PLACEHOLDER_PATTERN.fullmatch(normalized))


def _is_cash_like_name(value: str, normalized_name: str) -> bool:
    if not normalized_name or normalized_name in _CASH_NAME_TOKENS:
        return True
    if _CURRENCY_PLACEHOLDER_PATTERN.fullmatch(normalized_name):
        return True
    tokens = set(re.sub(r"[^A-Z0-9]+", " ", value.upper()).split())
    return bool(tokens & _CURRENCY_CODES) and bool(tokens & _CURRENCY_NAME_MARKERS)
