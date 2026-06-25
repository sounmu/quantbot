from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.entities import CollectionRun, Etf, Holding, HoldingChange, Metric, PricePoint
from app.domain.value_objects import holding_key


class FakeEtfRepository:
    def __init__(self) -> None:
        self._store: dict[str, Etf] = {}

    async def upsert(self, etf: Etf) -> None:
        self._store[etf.ticker] = etf

    async def get(self, ticker: str) -> Etf | None:
        return self._store.get(ticker.upper())

    async def list(self, **filters: object) -> tuple[list[Etf], int]:
        items = list(self._store.values())
        q = filters.get("q")
        issuer = filters.get("issuer")
        theme = filters.get("theme")
        if isinstance(q, str) and q:
            items = [
                item for item in items if q.upper() in item.ticker or q.lower() in item.name.lower()
            ]
        if isinstance(issuer, str) and issuer:
            items = [item for item in items if item.issuer == issuer]
        if isinstance(theme, str) and theme:
            items = [item for item in items if item.theme == theme]
        return items, len(items)

    async def issuers(self) -> list[str]:
        return sorted({item.issuer for item in self._store.values()})

    async def themes(self) -> list[str]:
        return sorted({item.theme for item in self._store.values() if item.theme})


class FakePriceRepository:
    def __init__(self) -> None:
        self._store: dict[str, list[PricePoint]] = {}

    async def upsert_many(self, prices: list[PricePoint]) -> int:
        for price in prices:
            self._store.setdefault(price.ticker, []).append(price)
        return len(prices)

    async def series(self, ticker: str, *, range_: str = "1y") -> list[PricePoint]:
        return sorted(self._store.get(ticker.upper(), []), key=lambda point: point.on)


class FakeHoldingRepository:
    def __init__(self) -> None:
        self._store: dict[str, list[Holding]] = {}

    async def upsert_many(self, holdings: list[Holding]) -> int:
        for holding in holdings:
            self._store.setdefault(holding.ticker, []).append(holding)
        return len(holdings)

    async def latest(self, ticker: str) -> list[Holding]:
        latest = await self.latest_snapshot_date(ticker)
        return await self.snapshot(ticker, latest) if latest else []

    async def snapshot(self, ticker: str, as_of_date: date) -> list[Holding]:
        return [
            holding
            for holding in self._store.get(ticker.upper(), [])
            if holding.as_of_date == as_of_date
        ]

    async def latest_snapshot_date(self, ticker: str) -> date | None:
        dates = {holding.as_of_date for holding in self._store.get(ticker.upper(), [])}
        return max(dates) if dates else None

    async def previous_snapshot_date(self, ticker: str, before: date) -> date | None:
        dates = {
            holding.as_of_date
            for holding in self._store.get(ticker.upper(), [])
            if holding.as_of_date < before
        }
        return max(dates) if dates else None

    async def snapshot_dates(self, ticker: str) -> list[date]:
        return sorted(
            {holding.as_of_date for holding in self._store.get(ticker.upper(), [])},
            reverse=True,
        )

    async def position_history(self, ticker: str, holding: str) -> list[Holding]:
        target = holding if holding.startswith("NAME:") else holding_key(holding, "")
        return [
            item
            for item in sorted(
                self._store.get(ticker.upper(), []), key=lambda point: point.as_of_date
            )
            if holding_key(item.holding_ticker, item.holding_name) == target
        ]


class FakeHoldingChangeRepository:
    def __init__(self) -> None:
        self._store: dict[tuple[str, date], list[HoldingChange]] = {}

    async def upsert_many(self, changes: list[HoldingChange]) -> int:
        if not changes:
            return 0
        self._store[(changes[0].ticker, changes[0].as_of_date)] = changes
        return len(changes)

    async def for_snapshot(
        self,
        ticker: str,
        *,
        as_of_date: date | None = None,
        include_unchanged: bool = False,
    ) -> list[HoldingChange]:
        ticker = ticker.upper()
        target_date = as_of_date
        if target_date is None:
            dates = [date_ for stored_ticker, date_ in self._store if stored_ticker == ticker]
            target_date = max(dates) if dates else None
        if target_date is None:
            return []
        changes = self._store.get((ticker, target_date), [])
        return (
            changes if include_unchanged else [c for c in changes if c.change_type != "UNCHANGED"]
        )

    async def for_position(self, ticker: str, holding: str) -> list[HoldingChange]:
        target = holding if holding.startswith("NAME:") else holding_key(holding, "")
        return [
            change
            for (stored_ticker, _), changes in self._store.items()
            if stored_ticker == ticker.upper()
            for change in changes
            if holding_key(change.holding_ticker, change.holding_name) == target
        ]

    async def recent(
        self,
        *,
        limit: int = 100,
        change_types: list[str] | None = None,
    ) -> list[HoldingChange]:
        changes = [change for stored in self._store.values() for change in stored]
        if change_types:
            changes = [change for change in changes if change.change_type in change_types]
        return sorted(changes, key=lambda change: change.as_of_date, reverse=True)[:limit]


class FakeMetricRepository:
    def __init__(self) -> None:
        self._store: dict[str, Metric] = {}

    async def upsert(self, metric: Metric) -> None:
        self._store[metric.ticker] = metric

    async def get(self, ticker: str) -> Metric | None:
        return self._store.get(ticker.upper())

    async def get_many(self, tickers: list[str]) -> dict[str, Metric]:
        return {ticker: self._store[ticker] for ticker in tickers if ticker in self._store}


class FakeCollectionRunRepository:
    async def start(self, job_name: str) -> CollectionRun:
        return CollectionRun(
            id=1, job_name=job_name, status="running", started_at=datetime.now(UTC)
        )

    async def finish(self, run_id: int, **kwargs: object) -> CollectionRun:
        return CollectionRun(
            id=run_id,
            job_name="test",
            status=str(kwargs["status"]),
            started_at=datetime.now(UTC),
            items_processed=int(kwargs["items_processed"]),
            error=kwargs.get("error") if isinstance(kwargs.get("error"), str) else None,
        )

    async def list_recent(self, *, limit: int = 20) -> list[CollectionRun]:
        return []
