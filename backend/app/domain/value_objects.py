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


def holding_key(holding_ticker: str | None, holding_name: str) -> str | None:
    if holding_ticker and holding_ticker.strip().upper() not in _CASH_TOKENS:
        return holding_ticker.strip().upper()

    normalized_name = re.sub(r"[^A-Z0-9]", "", holding_name.upper())
    if not normalized_name or normalized_name in _CASH_NAME_TOKENS:
        return None
    return f"NAME:{normalized_name}"
