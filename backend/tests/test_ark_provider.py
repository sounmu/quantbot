from __future__ import annotations

from app.infrastructure.external.holdings.ark_provider import ArkHoldingsProvider


def test_ark_provider_parses_official_csv_shape() -> None:
    csv_text = """date,fund,company,ticker,cusip,shares,market value ($),weight (%)
06/22/2026,ARKK,TESLA INC,TSLA,88160R101,"1,632,909","$653,963,725.41",9.68%
06/22/2026,ARKK,CASH & EQUIVALENTS,USD,,"1","$1.00",0.01%
"""

    holdings = ArkHoldingsProvider().parse_fixture("ARKK", csv_text)

    assert len(holdings) == 1
    assert holdings[0].holding_ticker == "TSLA"
    assert holdings[0].shares == 1_632_909
    assert holdings[0].market_value == 653_963_725.41
    assert holdings[0].weight == 9.68
