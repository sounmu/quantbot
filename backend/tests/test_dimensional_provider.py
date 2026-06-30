from __future__ import annotations

from datetime import date
from pathlib import Path

from app.infrastructure.external.holdings.dimensional_provider import DimensionalHoldingsProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_dimensional_parses_csv_shape_and_scales_weight() -> None:
    csv_text = (
        "date,etf_ticker,ticker,description,weight,market_value,identifier,isin,sedol,"
        "shares,coupon_rate,maturity_date,principal\n"
        "2026-06-26,DFAC,MCHP US,MICROCHIP TECHNOLOGY INC,0.000477915,22365171.36,"
        "595017104,US5950171042,2592174,254352.0,0.0,,22365171.36\n"
        "2026-06-26,DFAC,CASH US,CASH AND EQUIVALENTS,0.0001,100.0,,,,,0.0,,100.0\n"
    )

    holdings = DimensionalHoldingsProvider().parse_fixture("DFAC", csv_text)

    assert len(holdings) == 1  # cash row dropped
    holding = holdings[0]
    assert holding.holding_ticker == "MCHP"  # Bloomberg " US" suffix stripped
    assert holding.shares == 254352.0
    assert holding.market_value == 22365171.36
    assert abs(holding.weight - 0.0477915) < 1e-9  # fraction -> percent
    assert holding.security_id == "595017104"  # CUSIP from identifier column
    assert holding.as_of_date == date(2026, 6, 26)


def test_dimensional_parses_real_dfac_fixture() -> None:
    csv_text = (FIXTURES / "dimensional_dfac.csv").read_text()

    holdings = DimensionalHoldingsProvider().parse_fixture("DFAC", csv_text)

    assert holdings
    assert all(holding.shares is not None for holding in holdings)
    # Bloomberg country suffix is stripped from every resolved ticker.
    assert all(
        " " not in holding.holding_ticker for holding in holdings if holding.holding_ticker
    )
    assert all(holding.as_of_date == date(2026, 6, 26) for holding in holdings)


def test_dimensional_supports_only_us_equity_tickers() -> None:
    supported = DimensionalHoldingsProvider._SUPPORTED
    assert "DFAC" in supported
    assert "DFSV" in supported
    # International / fixed income are excluded from the provider universe.
    assert "DFAX" not in supported
    assert "DFCF" not in supported
