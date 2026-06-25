from __future__ import annotations

import re


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


class ChangeType:
    NEW = "NEW"
    EXIT = "EXIT"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    UNCHANGED = "UNCHANGED"


_CASH_TOKENS = {"", "--", "-", "CASH", "USD", "US DOLLAR", "DOLLAR", "MONEYMARKET"}
_CASH_NAME_TOKENS = {"CASH", "CASHEQUIVALENTS", "CASHANDEQUIVALENTS", "USD", "USDOLLAR"}


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
            and normalized_id not in _CASH_TOKENS
            and not normalized_id.startswith("999")
        ):
            return f"ID:{normalized_id}"

    if holding_ticker and holding_ticker.strip().upper() not in _CASH_TOKENS:
        return holding_ticker.strip().upper()

    normalized_name = re.sub(r"[^A-Z0-9]", "", holding_name.upper())
    if not normalized_name or normalized_name in _CASH_NAME_TOKENS:
        return None
    return f"NAME:{normalized_name}"
