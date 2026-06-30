from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from app.infrastructure.external.holdings.jpmorgan_provider import JPMorganHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _build_workbook() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Holdings"
    worksheet.append(["Holdings", "JPMorgan Active Value ETF - 46641Q167"])
    worksheet.append([None, None, None, None, None, None, None, "As of Date: 06/26/2026"])
    worksheet.append([])
    worksheet.append(
        [
            "Ticker",
            "Security Description",
            "Security Type",
            "Method",
            "Shares/Par",
            "Market Value (USD)",
            "Country",
            "Currency",
            "Sector",
            "Industry",
            "Coupon",
            "Maturity Date",
            "Effective Date",
            "Contract Size",
            "Strike Price",
            "% of Market Value",
            "% of Net Assets",
        ]
    )
    worksheet.append(
        ["ABBV", "ABBVIE INC COMMON STOCK", "DOMESTIC COMMON STOCK", "Physical",
         "3064257", "100000000", "United States", "USD", "Health Care", "Pharma",
         "0.0", "", "", "", "0.0", "1.80%", "1.74%"]
    )
    worksheet.append(
        ["MSFT US 09/2026 ELN", "EQUITY LINKED NOTE ON MSFT", "Equity Linked Notes", "Physical",
         "50000", "5000000", "United States", "USD", "", "", "0.0", "", "", "", "0.0", "0.10%", "0.09%"]
    )
    worksheet.append(
        ["", "US DOLLAR", "CURRENCIES", "Physical",
         "12345", "12345", "United States", "USD", "", "", "0.0", "", "", "", "0.0", "0.01%", "0.01%"]
    )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_jpmorgan_parses_equities_and_filters_elns_and_currency() -> None:
    holdings = JPMorganHoldingsProvider().parse_fixture("JAVA", _build_workbook())

    assert len(holdings) == 1
    holding = holdings[0]
    assert holding.holding_ticker == "ABBV"
    assert holding.shares == 3_064_257
    assert holding.market_value == 100_000_000
    assert holding.weight == 1.74
    assert holding.as_of_date == date(2026, 6, 26)
    # No CUSIP/ISIN column in the export -> ticker-based identity.
    assert holding.security_id is None


def test_jpmorgan_parses_official_jepq_xlsx_fixture() -> None:
    xlsx_bytes = (FIXTURES / "jpmorgan_jepq.xlsx").read_bytes()

    holdings = JPMorganHoldingsProvider().parse_fixture("JEPQ", xlsx_bytes)

    assert holdings, "expected equity holdings parsed from the real JEPQ export"
    # Every equity row carries a share count (ELNs were filtered out).
    assert all(holding.shares is not None for holding in holdings)
    assert all("LINKED NOTE" not in holding.holding_name.upper() for holding in holdings)
    assert holdings[0].holding_ticker == "NVDA"
    assert holdings[0].as_of_date == date(2026, 6, 26)


def test_jpmorgan_cusip_map_drives_known_tickers() -> None:
    cusips = JPMorganHoldingsProvider._CUSIPS
    assert cusips["JEPI"] == "46641Q332"
    assert cusips["JEPQ"] == "46654Q203"
    assert set(cusips) >= {"JEPI", "JEPQ", "JGRO", "JAVA", "JTEK", "JUSA", "JPSV"}
