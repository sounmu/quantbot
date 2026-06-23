from __future__ import annotations

import json
from pathlib import Path

from app.domain.entities import Etf
from app.domain.repositories import EtfRepository
from app.domain.value_objects import normalize_ticker

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "seed" / "active_etfs.json"


async def load_seed_universe(
    repo: EtfRepository,
    *,
    seed_path: Path = DEFAULT_SEED_PATH,
) -> int:
    rows = json.loads(seed_path.read_text(encoding="utf-8"))
    for row in rows:
        await repo.upsert(
            Etf(
                ticker=normalize_ticker(row["ticker"]),
                name=row["name"],
                issuer=row["issuer"],
                theme=row.get("theme"),
                expense_ratio=row.get("expense_ratio"),
                is_active_etf=True,
                discloses_daily=row.get("discloses_daily", False),
                currency=row.get("currency", "USD"),
                description=row.get("description"),
            )
        )
    return len(rows)
