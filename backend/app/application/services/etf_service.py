from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.application.services.metric_service import MetricService
from app.domain.entities import Etf, Holding, HoldingChange, Metric, PricePoint
from app.domain.repositories import (
    EtfRepository,
    HoldingChangeRepository,
    HoldingRepository,
    MetricRepository,
    PriceRepository,
)


@dataclass(slots=True)
class EtfWithMetric:
    etf: Etf
    metric: Metric | None


@dataclass(slots=True)
class CompareResult:
    items: list[EtfWithMetric]
    series: dict[str, list[dict[str, float | str]]]


class EtfService:
    def __init__(
        self,
        etfs: EtfRepository,
        prices: PriceRepository,
        holdings: HoldingRepository,
        changes: HoldingChangeRepository,
        metrics: MetricRepository,
        metric_service: MetricService | None = None,
    ) -> None:
        self._etfs = etfs
        self._prices = prices
        self._holdings = holdings
        self._changes = changes
        self._metrics = metrics
        self._metric_service = metric_service or MetricService()

    async def list_etfs(
        self,
        *,
        q: str | None = None,
        issuer: str | None = None,
        theme: str | None = None,
        sort: str = "name",
        order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[EtfWithMetric], int]:
        etfs, total = await self._etfs.list(
            q=q,
            issuer=issuer,
            theme=theme,
            sort=sort,
            order=order,
            page=page,
            page_size=page_size,
        )
        metric_map = await self._metrics.get_many([etf.ticker for etf in etfs])
        return [EtfWithMetric(etf=etf, metric=metric_map.get(etf.ticker)) for etf in etfs], total

    async def get_detail(self, ticker: str) -> EtfWithMetric | None:
        etf = await self._etfs.get(ticker)
        if etf is None:
            return None
        return EtfWithMetric(etf=etf, metric=await self._metrics.get(etf.ticker))

    async def get_prices(self, ticker: str, *, range_: str = "1y") -> list[PricePoint]:
        return await self._prices.series(ticker, range_=range_)

    async def get_holdings(self, ticker: str, *, as_of_date: date | None = None) -> list[Holding]:
        if as_of_date is None:
            return await self._holdings.latest(ticker)
        return await self._holdings.snapshot(ticker, as_of_date)

    async def get_holding_changes(
        self,
        ticker: str,
        *,
        as_of_date: date | None = None,
        include_unchanged: bool = False,
    ) -> list[HoldingChange]:
        return await self._changes.for_snapshot(
            ticker,
            as_of_date=as_of_date,
            include_unchanged=include_unchanged,
        )

    async def get_holding_dates(self, ticker: str) -> list[date]:
        return await self._holdings.snapshot_dates(ticker)

    async def get_position_history(self, ticker: str, holding: str) -> list[Holding]:
        return await self._holdings.position_history(ticker, holding)

    async def get_recent_changes(
        self,
        *,
        limit: int = 100,
        change_types: list[str] | None = None,
    ) -> list[HoldingChange]:
        return await self._changes.recent(limit=limit, change_types=change_types)

    async def compare(self, tickers: list[str], *, range_: str = "1y") -> CompareResult:
        selected: list[EtfWithMetric] = []
        series: dict[str, list[dict[str, float | str]]] = {}

        for ticker in tickers:
            detail = await self.get_detail(ticker)
            if detail is None:
                continue
            selected.append(detail)
            prices = await self.get_prices(ticker, range_=range_)
            series[ticker] = self._normalize_series(prices)

        return CompareResult(items=selected, series=series)

    async def issuers(self) -> list[str]:
        return await self._etfs.issuers()

    async def themes(self) -> list[str]:
        return await self._etfs.themes()

    def _normalize_series(self, prices: list[PricePoint]) -> list[dict[str, float | str]]:
        ordered = sorted(prices, key=lambda point: point.on)
        if not ordered:
            return []

        baseline = ordered[0].close
        if baseline <= 0:
            return []

        return [
            {
                "date": point.on.isoformat(),
                "close": point.close,
                "normalized_return": round(((point.close / baseline) - 1) * 100, 4),
            }
            for point in ordered
        ]
