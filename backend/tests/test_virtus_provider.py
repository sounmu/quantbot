from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.infrastructure.external.holdings.virtus_provider import VirtusHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_virtus_provider_normalizes_xls_rows_and_excludes_cash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = VirtusHoldingsProvider()

    def parse_xls_with_preamble(
        _xls_bytes: bytes,
        *,
        sheet: str | None = None,
        header_contains: str | tuple[str, ...] | None = None,
    ) -> tuple[dict[str, str], list[dict[str, Any]]]:
        return (
            {"as of": "Positions as of 6/18/2026"},
            [
                {
                    "name": "Flagstar Bank NA 6.375%",
                    "ticker": "FLG A",
                    "security type": "Preferred Stock",
                    "security id": "PFEP0524934",
                    "quantity": 2_639_678,
                    "(local)": 60_475_022.98,
                    "weight": "2.50%",
                },
                {
                    "name": "Cash/Cash equivalents",
                    "ticker": "",
                    "security type": "Cash",
                    "security id": "USD",
                    "quantity": -692_919_720.22,
                    "(local)": -692_919_720.22,
                    "weight": "-28.59%",
                },
            ],
        )

    monkeypatch.setattr(provider, "parse_xls_with_preamble", parse_xls_with_preamble)

    holdings = provider.parse_fixture("PFFA", b"fixture")

    assert len(holdings) == 1
    assert holdings[0].ticker == "PFFA"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "Flagstar Bank NA 6.375%"
    assert holdings[0].holding_ticker == "FLG A"
    assert holdings[0].shares == 2_639_678
    assert holdings[0].market_value == 60_475_022.98
    assert holdings[0].weight == 2.50


def test_virtus_provider_parses_xls_fixture_file() -> None:
    xls_bytes = (FIXTURES / "virtus_pffa.xls").read_bytes()

    holdings = VirtusHoldingsProvider().parse_fixture("PFFA", xls_bytes)

    assert len(holdings) == 2  # FLG A + JPM PR C (cash row excluded)
    assert holdings[0].ticker == "PFFA"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "Flagstar Bank NA 6.375%"
    assert holdings[0].holding_ticker == "FLG A"
    assert holdings[0].security_id == "PFEP0524934"
    assert holdings[0].shares == 2_639_678
    assert holdings[0].market_value == 60_475_022.98
    assert holdings[0].weight == 2.50
    assert holdings[1].holding_ticker == "JPM PR C"
    assert holdings[1].security_id == "PJPM0524935"
