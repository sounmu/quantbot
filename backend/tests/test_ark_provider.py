from __future__ import annotations

from pathlib import Path

from app.infrastructure.external.holdings.ark_provider import ArkHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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


def test_ark_provider_parses_fixture_file() -> None:
    csv_text = (FIXTURES / "ark_arkk.csv").read_text()

    holdings = ArkHoldingsProvider().parse_fixture("ARKK", csv_text)

    assert len(holdings) == 3  # 3 material holdings (cash row excluded)
    assert holdings[0].holding_ticker == "TSLA"
    assert holdings[0].shares == 1_632_909
    assert holdings[0].market_value == 653_963_725.41
    assert holdings[0].weight == 9.68
    assert holdings[1].holding_ticker == "ROKU"
    assert holdings[2].holding_ticker == "ZM"
