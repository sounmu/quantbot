from __future__ import annotations

from datetime import date

from app.domain.entities import Holding, HoldingChange
from app.domain.value_objects import ChangeType, holding_key


class HoldingChangeService:
    def __init__(self, *, shares_epsilon: float = 1.0, weight_epsilon: float = 0.0001) -> None:
        self._shares_epsilon = shares_epsilon
        self._weight_epsilon = weight_epsilon

    def diff(
        self,
        ticker: str,
        as_of: date,
        prev_date: date | None,
        current: list[Holding],
        previous: list[Holding],
    ) -> list[HoldingChange]:
        current_by_key = {
            key: holding
            for holding in current
            if (key := holding_key(holding.holding_ticker, holding.holding_name))
        }
        previous_by_key = {
            key: holding
            for holding in previous
            if (key := holding_key(holding.holding_ticker, holding.holding_name))
        }

        return [
            self._classify(ticker, as_of, prev_date, current_by_key.get(key), previous_by_key.get(key))
            for key in sorted(current_by_key.keys() | previous_by_key.keys())
        ]

    def _classify(
        self,
        ticker: str,
        as_of: date,
        prev_date: date | None,
        current: Holding | None,
        previous: Holding | None,
    ) -> HoldingChange:
        if current is not None and previous is None:
            return self._build(ticker, as_of, prev_date, current, previous, ChangeType.NEW)
        if current is None and previous is not None:
            return self._build(ticker, as_of, prev_date, current, previous, ChangeType.EXIT)

        shares_delta = self._delta(
            previous.shares if previous else None,
            current.shares if current else None,
        )
        weight_delta = self._delta(
            previous.weight if previous else None,
            current.weight if current else None,
        )

        if shares_delta is not None:
            if shares_delta > self._shares_epsilon:
                change_type = ChangeType.INCREASE
            elif shares_delta < -self._shares_epsilon:
                change_type = ChangeType.DECREASE
            else:
                change_type = ChangeType.UNCHANGED
        elif weight_delta is not None:
            if weight_delta > self._weight_epsilon:
                change_type = ChangeType.INCREASE
            elif weight_delta < -self._weight_epsilon:
                change_type = ChangeType.DECREASE
            else:
                change_type = ChangeType.UNCHANGED
        else:
            change_type = ChangeType.UNCHANGED

        return self._build(ticker, as_of, prev_date, current, previous, change_type)

    def _build(
        self,
        ticker: str,
        as_of: date,
        prev_date: date | None,
        current: Holding | None,
        previous: Holding | None,
        change_type: str,
    ) -> HoldingChange:
        shares_before = previous.shares if previous else None
        shares_after = current.shares if current else None
        shares_delta = self._delta(shares_before, shares_after)
        weight_before = previous.weight if previous else None
        weight_after = current.weight if current else None
        weight_delta = self._delta(weight_before, weight_after)

        name_source = current or previous
        return HoldingChange(
            ticker=ticker,
            as_of_date=as_of,
            prev_date=prev_date,
            holding_name=name_source.holding_name if name_source else "",
            holding_ticker=name_source.holding_ticker if name_source else None,
            change_type=change_type,
            shares_before=shares_before,
            shares_after=shares_after,
            shares_delta=shares_delta,
            shares_delta_pct=self._delta_pct(shares_before, shares_delta),
            weight_before=weight_before,
            weight_after=weight_after,
            weight_delta=weight_delta,
        )

    def _delta(self, before: float | None, after: float | None) -> float | None:
        if before is None and after is None:
            return None
        if before is None:
            return after
        if after is None:
            return -before
        return after - before

    def _delta_pct(self, before: float | None, delta: float | None) -> float | None:
        if before is None or before == 0 or delta is None:
            return None
        return round((delta / before) * 100, 4)
