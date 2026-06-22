from __future__ import annotations

from datetime import date

import pytest

from app.application.services.etf_service import EtfService
from app.application.services.metric_service import MetricService
from app.domain.entities import Etf, Metric, PricePoint
from tests.fakes import (
    FakeEtfRepository,
    FakeHoldingChangeRepository,
    FakeHoldingRepository,
    FakeMetricRepository,
    FakePriceRepository,
)


@pytest.mark.asyncio
async def test_list_etfs_filters_and_attaches_metrics() -> None:
    etfs = FakeEtfRepository()
    metrics = FakeMetricRepository()
    service = EtfService(
        etfs=etfs,
        prices=FakePriceRepository(),
        holdings=FakeHoldingRepository(),
        changes=FakeHoldingChangeRepository(),
        metrics=metrics,
    )

    await etfs.upsert(Etf(ticker="ARKK", name="ARK Innovation ETF", issuer="ARK", theme="Innovation"))
    await etfs.upsert(Etf(ticker="JEPI", name="JPMorgan Equity Premium Income ETF", issuer="JPMorgan"))
    await metrics.upsert(Metric(ticker="ARKK", as_of=date(2026, 1, 2), return_1y=12.3))

    items, total = await service.list_etfs(q="ark")

    assert total == 1
    assert items[0].etf.ticker == "ARKK"
    assert items[0].metric is not None
    assert items[0].metric.return_1y == 12.3


def test_metric_service_calculates_returns() -> None:
    service = MetricService()
    metric = service.calculate(
        "ARKK",
        [
            PricePoint(ticker="ARKK", on=date(2026, 1, 1), close=100),
            PricePoint(ticker="ARKK", on=date(2026, 2, 1), close=110),
            PricePoint(ticker="ARKK", on=date(2026, 3, 1), close=121),
        ],
    )

    assert metric is not None
    assert metric.return_ytd == 21
