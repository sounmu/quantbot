from __future__ import annotations

from datetime import date
from html import escape
import json

from app.infrastructure.external.holdings.trowe_price_provider import TRowePriceHoldingsProvider


def test_trowe_price_provider_parses_embedded_full_holdings_json() -> None:
    payload = {
        "full": {
            "effectiveDate": "2026-06-22T00:00:00Z",
            "holdings": [
                {
                    "name": "AMAZON.COM INC COMMON STOCK USD.01",
                    "tickerSymbol": "AMZN",
                    "marketValue": 433_288_073.43,
                    "percentageTotalNetAssets": 6.08126402,
                    "prioritizedIdentifier": "023135106",
                    "investmentType": "LT",
                    "shareQuantity": 1_772_937,
                },
                {
                    "name": "US DOLLAR",
                    "tickerSymbol": "USD",
                    "marketValue": 1.0,
                    "percentageTotalNetAssets": 0.01,
                    "prioritizedIdentifier": "CASH_USD",
                    "investmentType": "CASH",
                    "shareQuantity": 1.0,
                },
            ],
        }
    }
    html = f'<div data-component-object="{escape(json.dumps(payload))}"></div>'

    holdings = TRowePriceHoldingsProvider().parse_fixture("TCAF", html)

    assert len(holdings) == 1
    assert holdings[0].ticker == "TCAF"
    assert holdings[0].as_of_date == date(2026, 6, 22)
    assert holdings[0].holding_name == "AMAZON.COM INC COMMON STOCK USD.01"
    assert holdings[0].holding_ticker == "AMZN"
    assert holdings[0].shares == 1_772_937
    assert holdings[0].market_value == 433_288_073.43
    assert holdings[0].weight == 6.08126402
