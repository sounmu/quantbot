from __future__ import annotations

from datetime import date

import pytest

from app.application.services.flow_service import FlowService, decompose_flow
from app.domain.entities import Holding
from tests.fakes import FakeEtfFlowRepository, FakeHoldingRepository


PREV_DATE = date(2026, 1, 1)
CUR_DATE = date(2026, 1, 2)


def test_decompose_flow_classifies_pure_inflow_as_hold() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", PREV_DATE, "BBB", shares=200, price=20),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=110, price=10),
            _holding("ARKK", CUR_DATE, "BBB", shares=220, price=20),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    assert flow.net_flow == pytest.approx(500)
    assert flow.flow_rate == pytest.approx(0.1)
    assert flow.active_buy == pytest.approx(0)
    assert flow.active_sell == pytest.approx(0)
    assert flow.creation_r2 == pytest.approx(1)
    assert {component.flow_adjusted for component in components} == {"HOLD"}
    assert all(component.active_residual == pytest.approx(0) for component in components)


def test_decompose_flow_finds_active_buy_when_one_position_grows() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", PREV_DATE, "BBB", shares=100, price=10),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=150, price=10),
            _holding("ARKK", CUR_DATE, "BBB", shares=100, price=10),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    by_key = {component.holding_key: component for component in components}
    assert by_key["AAA"].flow_adjusted == "BUY"
    assert by_key["AAA"].active_residual == pytest.approx(25)
    assert by_key["BBB"].flow_adjusted == "SELL"
    assert flow.creation_r2 == pytest.approx(0.5)


def test_decompose_flow_handles_inflow_with_relative_sell() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=1),
            _holding("ARKK", PREV_DATE, "BBB", shares=100, price=100),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=90, price=1),
            _holding("ARKK", CUR_DATE, "BBB", shares=110, price=100),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    by_key = {component.holding_key: component for component in components}
    assert flow.net_flow > 0
    assert by_key["AAA"].flow_adjusted == "SELL"
    assert by_key["AAA"].active_residual < -1
    assert by_key["AAA"].active_intensity == "MEDIUM"
    assert by_key["BBB"].flow_adjusted == "BUY"
    assert by_key["BBB"].active_intensity == "MEDIUM"


def test_decompose_flow_treats_new_and_exit_as_active() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", PREV_DATE, "OLD", shares=50, price=10),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", CUR_DATE, "NEW", shares=20, price=10),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    by_key = {component.holding_key: component for component in components}
    assert by_key["NEW"].flow_adjusted == "BUY"
    assert by_key["NEW"].active_direction == "BUY"
    assert by_key["NEW"].active_intensity == "STRONG"
    assert by_key["NEW"].active_residual == pytest.approx(20)
    assert by_key["OLD"].flow_adjusted == "SELL"
    assert by_key["OLD"].active_direction == "SELL"
    assert by_key["OLD"].active_intensity == "STRONG"
    assert by_key["OLD"].active_residual == pytest.approx(-50)
    assert flow.turnover == pytest.approx(700 / 1200)


def test_decompose_flow_suppresses_tiny_matched_residuals() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100_000, price=10),
            _holding("ARKK", PREV_DATE, "BBB", shares=100_000, price=10),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=100_010, price=10),
            _holding("ARKK", CUR_DATE, "BBB", shares=100_009, price=10),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    assert {component.flow_adjusted for component in components} == {"HOLD"}
    assert {component.active_intensity for component in components} == {"NONE"}
    assert {component.active_direction for component in components} == {"NEUTRAL"}


def test_decompose_flow_returns_none_without_previous_or_denominator() -> None:
    no_prev, no_prev_components = decompose_flow(
        [],
        [_holding("ARKK", CUR_DATE, "AAA", shares=100, price=10)],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )
    zero_denom, zero_denom_components = decompose_flow(
        [_holding("ARKK", PREV_DATE, "AAA", shares=0, price=10)],
        [_holding("ARKK", CUR_DATE, "AAA", shares=100, price=10)],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert no_prev is None
    assert no_prev_components == []
    assert zero_denom is None
    assert zero_denom_components == []


def test_decompose_flow_skips_zero_share_rows_without_dividing_by_zero() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", PREV_DATE, "ZERO", shares=100, price=10),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=110, price=10),
            _holding("ARKK", CUR_DATE, "ZERO", shares=0, price=0),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    assert {component.holding_key for component in components} == {"AAA", "ZERO"}
    assert {component.holding_key: component.flow_adjusted for component in components}["ZERO"] == "SELL"


def test_decompose_flow_keeps_dollar_signs_consistent() -> None:
    flow, components = decompose_flow(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", PREV_DATE, "BBB", shares=100, price=20),
        ],
        [
            _holding("ARKK", CUR_DATE, "AAA", shares=130, price=10),
            _holding("ARKK", CUR_DATE, "BBB", shares=90, price=20),
        ],
        as_of_date=CUR_DATE,
        prev_date=PREV_DATE,
        ticker="ARKK",
    )

    assert flow is not None
    assert flow.active_buy > 0
    assert flow.active_sell > 0
    common_passive_dollars = sum(
        component.passive_shares * (10 if component.holding_key == "AAA" else 20)
        for component in components
    )
    assert flow.net_flow == pytest.approx(common_passive_dollars)


async def test_flow_service_recomputes_and_stores_etf_series() -> None:
    holdings = FakeHoldingRepository()
    flows = FakeEtfFlowRepository()
    service = FlowService(holdings=holdings, flows=flows)

    await holdings.upsert_many(
        [
            _holding("ARKK", PREV_DATE, "AAA", shares=100, price=10),
            _holding("ARKK", CUR_DATE, "AAA", shares=110, price=10),
        ]
    )

    written = await service.recompute_for_etf("ARKK")

    assert written == 1
    series = await service.series("ARKK")
    assert len(series) == 1
    assert series[0].flow_rate == pytest.approx(0.1)


def _holding(
    ticker: str,
    as_of_date: date,
    holding_ticker: str,
    *,
    shares: float,
    price: float,
) -> Holding:
    market_value = shares * price
    return Holding(
        ticker=ticker,
        as_of_date=as_of_date,
        holding_name=f"{holding_ticker} Inc",
        holding_ticker=holding_ticker,
        weight=market_value,
        shares=shares,
        market_value=market_value,
    )
