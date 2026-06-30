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


def test_ark_provider_uses_current_renamed_fund_slugs() -> None:
    assert (
        ArkHoldingsProvider._SLUGS["ARKF"]
        == "ARK_BLOCKCHAIN_&_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv"
    )
    assert ArkHoldingsProvider._SLUGS["ARKX"] == "ARK_SPACE_&_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv"


def test_ark_provider_normalizes_us_bloomberg_suffixes_only() -> None:
    csv_text = """date,fund,company,ticker,cusip,shares,market value ($),weight (%)
06/29/2026,ARKX,ROCKET LAB,RKLB UQ,773121108,"591,295","$10,000.00",5.71%
06/29/2026,ARKX,DRAFTKINGS INC-CL A,DKNG UW,26142V105,"12,345","$9,000.00",2.36%
06/29/2026,ARKX,NU HOLDINGS LTD/CAYMAN ISL-A,NU UN,G6683N103,"12,345","$9,000.00",2.01%
06/29/2026,ARKX,GARMIN LTD,GRMN UN,B3Z5T14,"12,345","$9,000.00",1.49%
06/29/2026,ARKX,DASSAULT SYSTEMES SE,DSY FP,B1YXBJ7,"12,345","$9,000.00",1.02%
06/29/2026,ARKX,JD LOGISTICS INC,2618,BM8Q5M0,"12,345","$9,000.00",0.92%
06/29/2026,ARKX,3IQ ETHER STAKING ETF,ETHQ/U,CA88557R1091,"12,345","$9,000.00",0.43%
"""

    holdings = ArkHoldingsProvider().parse_fixture("ARKX", csv_text)

    assert [holding.holding_ticker for holding in holdings] == [
        "RKLB",
        "DKNG",
        "NU",
        "GRMN",
        "DSY FP",
        "2618",
        "ETHQ/U",
    ]
