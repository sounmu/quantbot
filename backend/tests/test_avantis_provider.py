from __future__ import annotations

from datetime import date

from app.infrastructure.external.holdings.avantis_provider import AvantisHoldingsProvider


def test_avantis_provider_parses_embedded_etf_holdings_and_excludes_currency() -> None:
    html = (
        'a.portfolio={etfHoldingsAsOfDate:"06/18/2026",etfHoldings:['
        '{name:"MATSON INC COMMON STOCK",ticker:"MATX",securityType:"COMMON STOCK",'
        'cusip:"57686G105",isin:"US57686G1058",shareQuantity:"1519275",'
        'baseMarketValue:"290546151.00",weight:"1.03%"},'
        '{name:"VISCOFAN INTERIM COMMON STOCK NPV",ticker:"",'
        'securityType:"FOREIGN COMMON STOCK",cusip:"BV5LVC900",isin:"ES0184262055",'
        'shareQuantity:"7",baseMarketValue:"449.17",weight:"0.00%"},'
        '{name:"MATSON INC COMMON STOCK",ticker:"MATX",securityType:"COMMON STOCK",'
        'cusip:"57686G105",isin:"US57686G1058",shareQuantity:"25",'
        'baseMarketValue:"1000.00",weight:"0.01%"},'
        '{name:"US DOLLAR",ticker:"",securityType:null,cusip:"999USDZ92",'
        'shareQuantity:"3877574",baseMarketValue:"3877573.97",weight:"0.01%"}'
        "]};"
    )

    holdings = AvantisHoldingsProvider().parse_fixture("AVUV", html)

    assert len(holdings) == 2
    assert holdings[0].ticker == "AVUV"
    assert holdings[0].as_of_date == date(2026, 6, 18)
    assert holdings[0].holding_name == "MATSON INC COMMON STOCK"
    assert holdings[0].holding_ticker == "MATX"
    assert holdings[0].shares == 1_519_300
    assert holdings[0].market_value == 290_547_151
    assert holdings[0].weight == 1.04
    assert holdings[1].holding_ticker == "BV5LVC900"
