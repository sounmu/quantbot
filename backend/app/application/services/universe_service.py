from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace

from app.domain.entities import Etf
from app.domain.repositories import EtfRepository, MetricRepository


@dataclass(frozen=True, slots=True)
class SignalUniverseDecision:
    in_universe: bool
    reason: str


class SignalUniversePolicy:
    def __init__(self, *, min_aum: float, exchanges: list[str]) -> None:
        self.min_aum = min_aum
        self.exchanges = {_normalize_exchange(exchange) for exchange in exchanges if exchange}

    def evaluate(self, etf: Etf, *, aum: float | None = None) -> SignalUniverseDecision:
        effective_aum = aum if aum is not None else etf.aum
        if not etf.is_active_etf:
            return SignalUniverseDecision(False, "inactive")
        if not etf.discloses_daily:
            return SignalUniverseDecision(False, "non_daily_disclosure")
        if not etf.exchange:
            return SignalUniverseDecision(False, "missing_exchange")
        if _normalize_exchange(etf.exchange) not in self.exchanges:
            return SignalUniverseDecision(False, "exchange_not_allowed")
        if effective_aum is None or not math.isfinite(effective_aum):
            return SignalUniverseDecision(False, "missing_aum")
        if effective_aum < self.min_aum:
            return SignalUniverseDecision(False, "aum_below_min")
        return SignalUniverseDecision(True, "eligible")


async def refresh_signal_universe(
    etfs: EtfRepository,
    metrics: MetricRepository,
    policy: SignalUniversePolicy,
    *,
    page_size: int = 500,
) -> int:
    updated = 0
    page = 1
    while True:
        batch, total = await etfs.list(page=page, page_size=page_size)
        metric_map = await metrics.get_many([etf.ticker for etf in batch])
        for etf in batch:
            metric = metric_map.get(etf.ticker)
            aum = metric.aum if metric and metric.aum is not None else etf.aum
            decision = policy.evaluate(etf, aum=aum)
            refreshed = replace(
                etf,
                aum=aum,
                in_signal_universe=decision.in_universe,
                signal_universe_reason=decision.reason,
            )
            if refreshed != etf:
                await etfs.upsert(refreshed)
                updated += 1

        if page * page_size >= total or not batch:
            return updated
        page += 1


def _normalize_exchange(exchange: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", exchange.upper())
