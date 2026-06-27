from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.entities import Etf, Metric
from app.domain.repositories import EtfRepository, MetricRepository
from app.domain.value_objects import normalize_ticker

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "seed" / "active_etfs.json"


async def load_seed_universe(
    repo: EtfRepository,
    *,
    metrics: MetricRepository | None = None,
    seed_path: Path = DEFAULT_SEED_PATH,
) -> int:
    rows = json.loads(seed_path.read_text(encoding="utf-8"))
    for row in rows:
        ticker = normalize_ticker(row["ticker"])
        existing = await repo.get(ticker)
        seed_aum = _float_or_none(row.get("aum"))
        aum = seed_aum if seed_aum is not None else existing.aum if existing else None
        await repo.upsert(
            Etf(
                ticker=ticker,
                name=row["name"],
                issuer=row["issuer"],
                theme=row.get("theme"),
                expense_ratio=row.get("expense_ratio"),
                exchange=row.get("exchange") or (existing.exchange if existing else None),
                aum=aum,
                in_signal_universe=existing.in_signal_universe if existing else False,
                signal_universe_reason=existing.signal_universe_reason if existing else None,
                is_active_etf=True,
                discloses_daily=row.get("discloses_daily", False),
                currency=row.get("currency", "USD"),
                description=row.get("description"),
            )
        )
        if metrics is not None and seed_aum is not None:
            existing_metric = await metrics.get(ticker)
            await metrics.upsert(
                Metric(
                    ticker=ticker,
                    as_of=datetime.now(UTC).date(),
                    aum=seed_aum,
                    return_1m=existing_metric.return_1m if existing_metric else None,
                    return_3m=existing_metric.return_3m if existing_metric else None,
                    return_ytd=existing_metric.return_ytd if existing_metric else None,
                    return_1y=existing_metric.return_1y if existing_metric else None,
                )
            )
    return len(rows)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
