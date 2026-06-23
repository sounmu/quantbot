from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from app.infrastructure.external.holdings.base_csv import CsvHoldingsProviderBase


def test_parse_csv_with_preamble_detects_header_and_metadata() -> None:
    csv_text = """"Fund Holdings as of","Jun 19, 2026"
"Fund Name","iShares U.S. Equity Factor Rotation Active ETF"

Ticker,Name,Shares,Weight (%)
NVDA,NVIDIA CORP,"15,211,230",8.54
"""

    metadata, rows = CsvHoldingsProviderBase().parse_csv_with_preamble(
        csv_text,
        header_contains=("Ticker", "Weight (%)"),
    )

    assert metadata["fund holdings as of"] == "Jun 19, 2026"
    assert rows == [
        {
            "ticker": "NVDA",
            "name": "NVIDIA CORP",
            "shares": "15,211,230",
            "weight (%)": "8.54",
        }
    ]


def test_parse_xlsx_detects_header_and_normalizes_rows() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "holdings"
    worksheet.append(["Fund Name:", "Example Fund"])
    worksheet.append(["Holdings:", "As of 18-Jun-2026"])
    worksheet.append([])
    worksheet.append(["Name", "Identifier", "Weight", "Par Value"])
    worksheet.append(["US TREASURY N/B", "US91282CBJ99", 5.5, 245450000])

    buffer = BytesIO()
    workbook.save(buffer)

    metadata, rows = CsvHoldingsProviderBase().parse_xlsx_with_preamble(
        buffer.getvalue(),
        sheet="holdings",
        header_contains=("Name", "Weight"),
    )

    assert metadata["holdings"] == "As of 18-Jun-2026"
    assert rows == [
        {
            "name": "US TREASURY N/B",
            "identifier": "US91282CBJ99",
            "weight": 5.5,
            "par value": 245450000,
        }
    ]
