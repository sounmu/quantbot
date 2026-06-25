from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from app.infrastructure.external.holdings.spdr_provider import SpdrHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_spdr_provider_parses_xlsx_and_excludes_cash() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "holdings"
    worksheet.append(["Fund Name:", "State Street DoubleLine Total Return Tactical ETF"])
    worksheet.append(["Ticker Symbol:", "TOTL"])
    worksheet.append(["Holdings:", "As of 18-Jun-2026"])
    worksheet.append([])
    worksheet.append(
        [
            "Name",
            "Identifier",
            "SEDOL",
            "Weight",
            "Coupon",
            "Par Value",
            "Market Value",
            "Local Currency",
            "Maturity",
            "ISIN",
        ]
    )
    worksheet.append(
        [
            "US TREASURY N/B 0.75 01/31/2028",
            "US91282CBJ99",
            "BMZ2XM7",
            5.526658,
            0.75,
            245_450_000,
            232_463_201.23,
            "USD",
            "01/31/2028",
            "US91282CBJ99",
        ]
    )
    worksheet.append(["US Dollars", "CASH_USD", "-", 2.964288, "-", 1, 1, "USD", "-", "-"])

    buffer = BytesIO()
    workbook.save(buffer)

    holdings = SpdrHoldingsProvider().parse_fixture("TOTL", buffer.getvalue())

    assert len(holdings) == 1
    assert holdings[0].ticker == "TOTL"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "US TREASURY N/B 0.75 01/31/2028"
    assert holdings[0].holding_ticker == "US91282CBJ99"
    assert holdings[0].shares == 245_450_000
    assert holdings[0].market_value == 232_463_201.23
    assert holdings[0].weight == 5.526658


def test_spdr_provider_parses_xlsx_fixture_file() -> None:
    xlsx_bytes = (FIXTURES / "spdr_totl.xlsx").read_bytes()

    holdings = SpdrHoldingsProvider().parse_fixture("TOTL", xlsx_bytes)

    assert len(holdings) == 2  # 2 bonds (cash row excluded)
    assert holdings[0].ticker == "TOTL"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "US TREASURY N/B 0.75 01/31/2028"
    assert holdings[0].holding_ticker == "US91282CBJ99"
    assert holdings[0].security_id == "US91282CBJ99"
    assert holdings[0].shares == 245_450_000
    assert holdings[0].market_value == 232_463_201.23
    assert holdings[0].weight == 5.526658
    assert holdings[1].holding_name == "FHLMC MULTIFAMILY STRUCTURED P/T 2.45 07/25/2029"
