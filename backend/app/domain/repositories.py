from __future__ import annotations

from typing import Protocol

from datetime import date

from app.domain.entities import CollectionRun, Etf, Holding, HoldingChange, Metric, PricePoint


class EtfRepository(Protocol):
    async def upsert(self, etf: Etf) -> None: ...

    async def get(self, ticker: str) -> Etf | None: ...

    async def list(
        self,
        *,
        q: str | None = None,
        issuer: str | None = None,
        theme: str | None = None,
        sort: str = "name",
        order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Etf], int]: ...

    async def issuers(self) -> list[str]: ...

    async def themes(self) -> list[str]: ...


class PriceRepository(Protocol):
    async def upsert_many(self, prices: list[PricePoint]) -> int: ...

    async def series(self, ticker: str, *, range_: str = "1y") -> list[PricePoint]: ...


class HoldingRepository(Protocol):
    async def upsert_many(self, holdings: list[Holding]) -> int: ...

    async def latest(self, ticker: str) -> list[Holding]: ...

    async def snapshot(self, ticker: str, as_of_date: date) -> list[Holding]: ...

    async def latest_snapshot_date(self, ticker: str) -> date | None: ...

    async def previous_snapshot_date(self, ticker: str, before: date) -> date | None: ...

    async def snapshot_dates(self, ticker: str) -> list[date]: ...

    async def position_history(self, ticker: str, holding: str) -> list[Holding]: ...


class HoldingChangeRepository(Protocol):
    async def upsert_many(self, changes: list[HoldingChange]) -> int: ...

    async def for_snapshot(
        self,
        ticker: str,
        *,
        as_of_date: date | None = None,
        include_unchanged: bool = False,
    ) -> list[HoldingChange]: ...

    async def for_position(self, ticker: str, holding: str) -> list[HoldingChange]: ...

    async def recent(
        self,
        *,
        limit: int = 100,
        change_types: list[str] | None = None,
    ) -> list[HoldingChange]: ...


class MetricRepository(Protocol):
    async def upsert(self, metric: Metric) -> None: ...

    async def get(self, ticker: str) -> Metric | None: ...

    async def get_many(self, tickers: list[str]) -> dict[str, Metric]: ...


class CollectionRunRepository(Protocol):
    async def start(self, job_name: str) -> CollectionRun: ...

    async def finish(
        self,
        run_id: int,
        *,
        status: str,
        items_processed: int,
        error: str | None = None,
    ) -> CollectionRun: ...

    async def list_recent(self, *, limit: int = 20) -> list[CollectionRun]: ...
