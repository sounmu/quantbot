from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.infrastructure.external.holdings.capital_group_provider import CapitalGroupHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_capital_group_provider_parses_daily_holdings_xlsx_and_excludes_cash() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Daily Fund Holdings"
    worksheet.append(
        [
            "Holdings for ETF",
            "CGGR - Capital Group Growth ETF",
            None,
            None,
            None,
            None,
            "As Of 06/18/2026",
        ]
    )
    worksheet.append([])
    worksheet.append(
        [
            "Security Name",
            "Ticker",
            "Asset Type",
            "Shares or Principal Amount",
            "Market Value",
            "Percent of Net Assets",
            "CUSIP",
            "ISIN",
            "SEDOL 1",
            "Notional Value",
        ]
    )
    worksheet.append(
        [
            "META PLATFORMS INC CLASS A COMMON STOCK USD.000006",
            "META",
            "Equity",
            2_814_677,
            1_624_687_857.94,
            0.0657,
            "30303M102",
            "US30303M1027",
            "B7TL820",
            "--",
        ]
    )
    worksheet.append(
        [
            "CAPITAL GROUP CENTRAL CASH FUN CAPITAL GROUP CNTRL CSH M",
            "CMQXX",
            "Cash & Equivalent",
            6_011_452.26,
            601_205_340.72,
            0.0243,
            "14020B102",
            "US14020B1026",
            None,
            "--",
        ]
    )

    buffer = BytesIO()
    workbook.save(buffer)

    holdings = CapitalGroupHoldingsProvider().parse_fixture("CGGR", buffer.getvalue())

    assert len(holdings) == 1
    assert holdings[0].ticker == "CGGR"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "META PLATFORMS INC CLASS A COMMON STOCK USD.000006"
    assert holdings[0].holding_ticker == "META"
    assert holdings[0].shares == 2_814_677
    assert holdings[0].market_value == 1_624_687_857.94
    assert holdings[0].weight == pytest.approx(6.57)


def test_capital_group_provider_parses_xlsx_fixture_file() -> None:
    xlsx_bytes = (FIXTURES / "capital_group_cggr.xlsx").read_bytes()

    holdings = CapitalGroupHoldingsProvider().parse_fixture("CGGR", xlsx_bytes)

    assert len(holdings) == 3  # META, MSFT, AMZN (cash row excluded)
    assert holdings[0].ticker == "CGGR"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "META PLATFORMS INC CLASS A COMMON STOCK USD.000006"
    assert holdings[0].holding_ticker == "META"
    assert holdings[0].security_id == "30303M102"
    assert holdings[0].shares == 2_814_677
    assert holdings[0].market_value == 1_624_687_857.94
    assert holdings[0].weight == pytest.approx(6.57)
    assert holdings[1].holding_ticker == "MSFT"
    assert holdings[2].holding_ticker == "AMZN"
