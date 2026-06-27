from __future__ import annotations

from datetime import date

from app.application.services.signal_service import SignalService, aggregate_daily_signals
from app.domain.entities import HoldingChange, SecurityPrice
from app.domain.value_objects import ChangeType
from tests.fakes import (
    FakeHoldingChangeRepository,
    FakeSecurityPriceRepository,
    FakeSignalDailyRepository,
)


def test_aggregate_daily_signals_counts_cross_etf_conviction_and_flows() -> None:
    signals = aggregate_daily_signals(
        [
            _change("ARKK", "TSLA", ChangeType.INCREASE, shares_delta=10),
            _change("DYNF", "TSLA", ChangeType.NEW, shares_delta=5),
            _change("ARKW", "ROKU", ChangeType.DECREASE, shares_delta=-4),
            _change("ARKF", "NOISE", ChangeType.UNCHANGED, shares_delta=0),
        ],
        {"TSLA": 200, "ROKU": 50},
    )

    assert [(signal.security_key, signal.conviction_score) for signal in signals] == [
        ("TSLA", 2),
        ("ROKU", -1),
    ]
    tsla = signals[0]
    assert tsla.n_buying == 2
    assert tsla.n_selling == 0
    assert tsla.net_shares_flow == 15
    assert tsla.net_dollar_flow == 3000


async def test_signal_service_recomputes_and_returns_participants() -> None:
    changes = FakeHoldingChangeRepository()
    prices = FakeSecurityPriceRepository()
    signals = FakeSignalDailyRepository()
    service = SignalService(changes=changes, security_prices=prices, signals=signals)

    await changes.upsert_many(
        [
            _change("ARKK", "TSLA", ChangeType.INCREASE, shares_delta=10),
            _change("DYNF", "TSLA", ChangeType.NEW, shares_delta=5),
        ]
    )
    await prices.upsert_many(
        [SecurityPrice("TSLA", date(2026, 1, 2), close=210, adj_close=200)]
    )

    written = await service.recompute_daily(as_of_date=date(2026, 1, 2))

    assert written == 1
    daily = await service.daily(as_of_date=date(2026, 1, 2))
    assert daily[0].security_key == "TSLA"
    assert daily[0].conviction_score == 2

    history = await service.for_security("TSLA")
    assert len(history) == 1
    assert [participant.etf_ticker for participant in history[0].participants] == [
        "ARKK",
        "DYNF",
    ]


async def test_signal_service_clears_a_date_when_no_priceable_changes_remain() -> None:
    changes = FakeHoldingChangeRepository()
    prices = FakeSecurityPriceRepository()
    signals = FakeSignalDailyRepository()
    service = SignalService(changes=changes, security_prices=prices, signals=signals)

    await signals.replace_for_dates(
        [date(2026, 1, 2)],
        [
            aggregate_daily_signals(
                [_change("ARKK", "TSLA", ChangeType.NEW, shares_delta=10)],
                {"TSLA": 200},
            )[0]
        ],
    )

    written = await service.recompute_daily(as_of_date=date(2026, 1, 2))

    assert written == 0
    assert await service.daily(as_of_date=date(2026, 1, 2)) == []


def _change(
    etf: str,
    ticker: str,
    change_type: str,
    *,
    shares_delta: float | None,
) -> HoldingChange:
    shares_before = None if change_type == ChangeType.NEW else 100
    shares_after = None if change_type == ChangeType.EXIT else (shares_before or 0) + (shares_delta or 0)
    return HoldingChange(
        ticker=etf,
        as_of_date=date(2026, 1, 2),
        prev_date=date(2026, 1, 1),
        holding_name=f"{ticker} Inc",
        holding_ticker=ticker,
        change_type=change_type,
        shares_before=shares_before,
        shares_after=shares_after,
        shares_delta=shares_delta,
        shares_delta_pct=None,
        weight_before=1.0,
        weight_after=1.1,
        weight_delta=0.1,
    )
