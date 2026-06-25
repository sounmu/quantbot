from __future__ import annotations

from datetime import date

import pytest

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


def test_diff_rejects_missing_shares_for_matched_holding() -> None:
    service = HoldingChangeService()

    with pytest.raises(ValueError, match="missing shares"):
        service.diff(
            "ARKK",
            date(2026, 1, 2),
            date(2026, 1, 1),
            [Holding("ARKK", date(2026, 1, 2), "Tesla", 11, "TSLA", shares=None)],
            [Holding("ARKK", date(2026, 1, 1), "Tesla", 10, "TSLA", shares=100)],
        )


def test_diff_disambiguates_same_ticker_by_security_id() -> None:
    # International ETFs (e.g. AVDV) reuse local exchange tickers across different companies.
    # The security identifier keeps them distinct instead of colliding on the shared ticker.
    service = HoldingChangeService(shares_epsilon=1)
    current = [
        Holding(
            "AVDV", date(2026, 1, 2), "DRAX GROUP PLC", 1.0, "DRX", shares=100,
            security_id="GB0009633180",
        ),
        Holding(
            "AVDV", date(2026, 1, 2), "ADF GROUP INC", 0.5, "DRX", shares=50,
            security_id="CA0008681011",
        ),
    ]

    changes = service.diff("AVDV", date(2026, 1, 2), None, current, [])

    assert len(changes) == 2
    assert {change.holding_name for change in changes} == {"DRAX GROUP PLC", "ADF GROUP INC"}
    assert all(change.change_type == ChangeType.NEW for change in changes)
    assert all(change.security_id is not None for change in changes)


def test_diff_rejects_duplicate_holding_keys() -> None:
    service = HoldingChangeService()

    with pytest.raises(ValueError, match="Duplicate holding key"):
        service.diff(
            "ARKK",
            date(2026, 1, 2),
            date(2026, 1, 1),
            [
                Holding("ARKK", date(2026, 1, 2), "Tesla Inc", 10, "TSLA", shares=100),
                Holding("ARKK", date(2026, 1, 2), "Tesla Motors", 1, "TSLA", shares=10),
            ],
            [],
        )
