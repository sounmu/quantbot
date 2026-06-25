from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.infrastructure.external.holdings.ishares_provider import ISharesHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_ishares_provider_parses_preamble_csv_and_excludes_cash() -> None:
    csv_text = """"Fund Holdings as of","Jun 19, 2026"
"Fund Name","iShares U.S. Equity Factor Rotation Active ETF"

Ticker,Name,Shares,Market Value,Weight (%),Asset Class
NVDA,NVIDIA CORP,"15,211,230","3,204,854,048.70",8.54,Equity
USD,US Dollars,"1","1.00",0.01,Cash and/or Derivatives
"""

    holdings = ISharesHoldingsProvider().parse_fixture("DYNF", csv_text)

    assert len(holdings) == 1
    assert holdings[0].ticker == "DYNF"
    assert holdings[0].as_of_date == date(2026, 6, 19)
    assert holdings[0].holding_ticker == "NVDA"
    assert holdings[0].shares == 15_211_230
    assert holdings[0].market_value == 3_204_854_048.70
    assert holdings[0].weight == 8.54


def test_ishares_provider_parses_product_data_json_shape() -> None:
    data = {
        "componentsByNameMap": {
            "holdings": {
                "containersByNameMap": {
                    "all": {
                        "dataPointsByNameMap": {
                            "asOfDate": {"formattedValue": "Jun 19, 2026", "value": 20260619},
                            "ticker": {"value": ["AAPL", "USD"]},
                            "issueName": {"value": ["APPLE INC", "US Dollars"]},
                            "unitsHeld": {"value": [9_482_129.0, 1.0]},
                            "marketValue": {"value": [2_825_769_263.29, 1.0]},
                            "holdingPercent": {"value": [7.5294, 0.01]},
                            "assetClass": {"value": ["Equity", "Cash and/or Derivatives"]},
                        }
                    }
                }
            }
        }
    }

    holdings = ISharesHoldingsProvider().parse_json_fixture("DYNF", data)

    assert len(holdings) == 1
    assert holdings[0].as_of_date == date(2026, 6, 19)
    assert holdings[0].holding_ticker == "AAPL"
    assert holdings[0].shares == 9_482_129
    assert holdings[0].market_value == 2_825_769_263.29
    assert holdings[0].weight == 7.5294


def test_ishares_provider_parses_csv_fixture_file() -> None:
    csv_text = (FIXTURES / "ishares_dynf.csv").read_text()

    holdings = ISharesHoldingsProvider().parse_fixture("DYNF", csv_text)

    assert len(holdings) == 3  # NVDA, AAPL, MSFT (USD cash row excluded)
    assert holdings[0].ticker == "DYNF"
    assert holdings[0].as_of_date == date(2026, 6, 19)
    assert holdings[0].holding_ticker == "NVDA"
    assert holdings[0].shares == 15_211_230
    assert holdings[0].market_value == 3_204_854_048.70
    assert holdings[0].weight == 8.54
    assert holdings[1].holding_ticker == "AAPL"
    assert holdings[2].holding_ticker == "MSFT"


def test_ishares_provider_parses_json_fixture_file() -> None:
    data = json.loads((FIXTURES / "ishares_dynf.json").read_text())

    holdings = ISharesHoldingsProvider().parse_json_fixture("DYNF", data)

    assert len(holdings) == 3  # NVDA, AAPL, MSFT (USD excluded)
    assert holdings[0].as_of_date == date(2026, 6, 19)
    assert holdings[0].holding_ticker == "NVDA"
    assert holdings[0].shares == 15_211_230
    assert holdings[0].market_value == 3_204_854_048.70
    assert holdings[0].weight == 8.54
    assert holdings[1].holding_ticker == "AAPL"
    assert holdings[2].holding_ticker == "MSFT"
