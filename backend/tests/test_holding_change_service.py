from __future__ import annotations

from datetime import date

from app.application.services.holding_change_service import HoldingChangeService
from app.domain.entities import Holding
from app.domain.value_objects import ChangeType


def test_diff_classifies_new_exit_increase_decrease_and_unchanged() -> None:
    service = HoldingChangeService(shares_epsilon=1)
    previous = [
        Holding("ARKK", date(2026, 1, 1), "Tesla", 10, "TSLA", shares=100),
        Holding("ARKK", date(2026, 1, 1), "Roku", 5, "ROKU", shares=100),
        Holding("ARKK", date(2026, 1, 1), "Zoom", 3, "ZM", shares=50),
        Holding("ARKK", date(2026, 1, 1), "Noise", 1, "NOISE", shares=10),
    ]
    current = [
        Holding("ARKK", date(2026, 1, 2), "Tesla", 11, "TSLA", shares=120),
        Holding("ARKK", date(2026, 1, 2), "Roku", 4, "ROKU", shares=80),
        Holding("ARKK", date(2026, 1, 2), "Coinbase", 2, "COIN", shares=10),
        Holding("ARKK", date(2026, 1, 2), "Noise", 1.1, "NOISE", shares=10.5),
    ]

    changes = {
        change.holding_ticker: change
        for change in service.diff("ARKK", date(2026, 1, 2), date(2026, 1, 1), current, previous)
    }

    assert changes["TSLA"].change_type == ChangeType.INCREASE
    assert changes["TSLA"].shares_delta == 20
    assert changes["ROKU"].change_type == ChangeType.DECREASE
    assert changes["COIN"].change_type == ChangeType.NEW
    assert changes["ZM"].change_type == ChangeType.EXIT
    assert changes["NOISE"].change_type == ChangeType.UNCHANGED


def test_diff_uses_name_fallback_and_ignores_cash() -> None:
    service = HoldingChangeService()
    previous = [
        Holding("ARKK", date(2026, 1, 1), "Private Company Inc", 1, None, shares=10),
        Holding("ARKK", date(2026, 1, 1), "CASH", 1, "USD", shares=1),
    ]
    current = [
        Holding("ARKK", date(2026, 1, 2), "Private Company Inc.", 2, None, shares=20),
        Holding("ARKK", date(2026, 1, 2), "CASH", 1, "USD", shares=1),
    ]

    changes = service.diff("ARKK", date(2026, 1, 2), date(2026, 1, 1), current, previous)

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.INCREASE
    assert changes[0].holding_ticker is None

