from __future__ import annotations

from datetime import date

import pytest

from app.application.pipeline.collect import prepare_holdings_batch
from app.domain.entities import Etf, Holding


def test_prepare_holdings_batch_rejects_empty_result() -> None:
    with pytest.raises(ValueError, match="returned no holdings"):
        prepare_holdings_batch(Etf("ARKK", "ARKK", "ARK"), [])


def test_prepare_holdings_batch_rejects_mixed_snapshot_dates() -> None:
    etf = Etf("ARKK", "ARKK", "ARK")

    with pytest.raises(ValueError, match="Invalid holdings batch"):
        prepare_holdings_batch(
            etf,
            [
                Holding("ARKK", date(2026, 1, 1), "Tesla", 10, "TSLA", shares=100),
                Holding("ARKK", date(2026, 1, 2), "Roku", 5, "ROKU", shares=100),
            ],
        )


def test_prepare_holdings_batch_rejects_material_missing_shares() -> None:
    etf = Etf("ARKK", "ARKK", "ARK")

    with pytest.raises(ValueError, match="Missing shares"):
        prepare_holdings_batch(
            etf,
            [Holding("ARKK", date(2026, 1, 1), "Tesla", 10, "TSLA", shares=None)],
        )


def test_prepare_holdings_batch_merges_duplicate_holding_keys_and_skips_zero_rows() -> None:
    etf = Etf("TOTL", "SPDR DoubleLine Total Return Tactical ETF", "State Street")

    prepared = prepare_holdings_batch(
        etf,
        [
            Holding("TOTL", date(2026, 1, 1), "Emerald Expo Bond", 0.1, None, shares=90),
            Holding("TOTL", date(2026, 1, 1), "Emerald Expo Bond", 0.2, None, shares=10),
            Holding("TOTL", date(2026, 1, 1), "Stale Zero", 0, "ZERO", shares=0, market_value=0),
        ],
    )

    assert len(prepared) == 1
    assert prepared[0].shares == 100
    assert prepared[0].weight == pytest.approx(0.3)
