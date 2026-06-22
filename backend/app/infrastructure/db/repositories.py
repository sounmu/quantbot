from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, delete, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import CollectionRun, Etf, Holding, HoldingChange, Metric, PricePoint
from app.domain.value_objects import ChangeType, holding_key, normalize_ticker
from app.infrastructure.db import mappers
from app.infrastructure.db.orm_models import (
    CollectionRunORM,
    EtfHoldingChangeORM,
    EtfHoldingORM,
    EtfMetricORM,
    EtfORM,
    EtfPriceORM,
)


class SqlAlchemyEtfRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert(self, etf: Etf) -> None:
        ticker = normalize_ticker(etf.ticker)
        row = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == ticker))
        if row is None:
            self._s.add(
                EtfORM(
                    ticker=ticker,
                    name=etf.name,
                    issuer=etf.issuer,
                    theme=etf.theme,
                    expense_ratio=etf.expense_ratio,
                    inception_date=etf.inception_date,
                    is_active_etf=etf.is_active_etf,
                    discloses_daily=etf.discloses_daily,
                    currency=etf.currency,
                    description=etf.description,
                )
            )
            return

        row.name = etf.name
        row.issuer = etf.issuer
        row.theme = etf.theme
        row.expense_ratio = etf.expense_ratio
        row.inception_date = etf.inception_date
        row.is_active_etf = etf.is_active_etf
        row.discloses_daily = etf.discloses_daily
        row.currency = etf.currency
        row.description = etf.description

    async def get(self, ticker: str) -> Etf | None:
        row = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        return mappers.to_etf(row) if row else None

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
    ) -> tuple[list[Etf], int]:
        stmt: Select[tuple[EtfORM]] = select(EtfORM)
        count_stmt = select(func.count()).select_from(EtfORM)

        filters = []
        if q:
            like = f"%{q.strip()}%"
            filters.append(or_(EtfORM.ticker.ilike(like), EtfORM.name.ilike(like)))
        if issuer:
            filters.append(EtfORM.issuer == issuer)
        if theme:
            filters.append(EtfORM.theme == theme)

        for clause in filters:
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)

        if sort in {"return_1y", "return_ytd"}:
            stmt = stmt.outerjoin(EtfMetricORM)
            sort_column = getattr(EtfMetricORM, sort)
        elif sort == "expense_ratio":
            sort_column = EtfORM.expense_ratio
        else:
            sort_column = EtfORM.name

        stmt = stmt.order_by(sort_column.desc().nullslast() if order == "desc" else sort_column.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        rows = (await self._s.scalars(stmt)).all()
        total = await self._s.scalar(count_stmt)
        return [mappers.to_etf(row) for row in rows], int(total or 0)

    async def issuers(self) -> list[str]:
        rows = await self._s.scalars(select(distinct(EtfORM.issuer)).order_by(EtfORM.issuer))
        return [row for row in rows.all() if row]

    async def themes(self) -> list[str]:
        rows = await self._s.scalars(select(distinct(EtfORM.theme)).order_by(EtfORM.theme))
        return [row for row in rows.all() if row]


class SqlAlchemyPriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, prices: list[PricePoint]) -> int:
        processed = 0
        for price in prices:
            etf = await self._s.scalar(
                select(EtfORM).where(EtfORM.ticker == normalize_ticker(price.ticker))
            )
            if etf is None:
                continue

            row = await self._s.scalar(
                select(EtfPriceORM).where(
                    EtfPriceORM.etf_id == etf.id,
                    EtfPriceORM.date == price.on,
                )
            )
            if row is None:
                self._s.add(
                    EtfPriceORM(
                        etf_id=etf.id,
                        date=price.on,
                        open=price.open,
                        high=price.high,
                        low=price.low,
                        close=price.close,
                        nav=price.nav,
                        volume=price.volume,
                    )
                )
            else:
                row.open = price.open
                row.high = price.high
                row.low = price.low
                row.close = price.close
                row.nav = price.nav
                row.volume = price.volume
            processed += 1
        return processed

    async def series(self, ticker: str, *, range_: str = "1y") -> list[PricePoint]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        stmt = select(EtfPriceORM).options(selectinload(EtfPriceORM.etf)).where(EtfPriceORM.etf_id == etf.id)
        since = self._range_start(range_)
        if since is not None:
            stmt = stmt.where(EtfPriceORM.date >= since)
        stmt = stmt.order_by(EtfPriceORM.date.asc())
        rows = (await self._s.scalars(stmt)).all()
        return [mappers.to_price(row) for row in rows]

    def _range_start(self, range_: str) -> date | None:
        today = date.today()
        match range_:
            case "1m":
                return today - timedelta(days=31)
            case "3m":
                return today - timedelta(days=93)
            case "6m":
                return today - timedelta(days=186)
            case "1y":
                return today - timedelta(days=366)
            case "ytd":
                return date(today.year, 1, 1)
            case "max":
                return None
            case _:
                return today - timedelta(days=366)


class SqlAlchemyHoldingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, holdings: list[Holding]) -> int:
        if not holdings:
            return 0

        etf = await self._s.scalar(
            select(EtfORM).where(EtfORM.ticker == normalize_ticker(holdings[0].ticker))
        )
        if etf is None:
            return 0

        as_of_date = holdings[0].as_of_date
        await self._s.execute(
            delete(EtfHoldingORM).where(
                EtfHoldingORM.etf_id == etf.id,
                EtfHoldingORM.as_of_date == as_of_date,
            )
        )
        for holding in holdings:
            self._s.add(
                EtfHoldingORM(
                    etf_id=etf.id,
                    as_of_date=holding.as_of_date,
                    holding_ticker=holding.holding_ticker,
                    holding_name=holding.holding_name,
                    weight=holding.weight,
                    shares=holding.shares,
                    market_value=holding.market_value,
                )
            )
        return len(holdings)

    async def latest(self, ticker: str) -> list[Holding]:
        latest_date = await self.latest_snapshot_date(ticker)
        if latest_date is None:
            return []
        return await self.snapshot(ticker, latest_date)

    async def snapshot(self, ticker: str, as_of_date: date) -> list[Holding]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        rows = (
            await self._s.scalars(
                select(EtfHoldingORM)
                .options(selectinload(EtfHoldingORM.etf))
                .where(EtfHoldingORM.etf_id == etf.id, EtfHoldingORM.as_of_date == as_of_date)
                .order_by(EtfHoldingORM.weight.desc())
            )
        ).all()
        return [mappers.to_holding(row) for row in rows]

    async def latest_snapshot_date(self, ticker: str) -> date | None:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return None

        latest_date = await self._s.scalar(
            select(func.max(EtfHoldingORM.as_of_date)).where(EtfHoldingORM.etf_id == etf.id)
        )
        return latest_date

    async def previous_snapshot_date(self, ticker: str, before: date) -> date | None:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return None

        return await self._s.scalar(
            select(func.max(EtfHoldingORM.as_of_date)).where(
                EtfHoldingORM.etf_id == etf.id,
                EtfHoldingORM.as_of_date < before,
            )
        )

    async def snapshot_dates(self, ticker: str) -> list[date]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        rows = await self._s.scalars(
            select(distinct(EtfHoldingORM.as_of_date))
            .where(EtfHoldingORM.etf_id == etf.id)
            .order_by(EtfHoldingORM.as_of_date.desc())
        )
        return list(rows.all())

    async def position_history(self, ticker: str, holding: str) -> list[Holding]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        target = holding if holding.startswith("NAME:") else holding_key(holding, "")
        rows = (
            await self._s.scalars(
                select(EtfHoldingORM)
                .options(selectinload(EtfHoldingORM.etf))
                .where(EtfHoldingORM.etf_id == etf.id)
                .order_by(EtfHoldingORM.as_of_date.asc())
            )
        ).all()
        return [
            mappers.to_holding(row)
            for row in rows
            if holding_key(row.holding_ticker, row.holding_name) == target
        ]


class SqlAlchemyHoldingChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, changes: list[HoldingChange]) -> int:
        if not changes:
            return 0

        etf = await self._s.scalar(
            select(EtfORM).where(EtfORM.ticker == normalize_ticker(changes[0].ticker))
        )
        if etf is None:
            return 0

        as_of_date = changes[0].as_of_date
        await self._s.execute(
            delete(EtfHoldingChangeORM).where(
                EtfHoldingChangeORM.etf_id == etf.id,
                EtfHoldingChangeORM.as_of_date == as_of_date,
            )
        )
        for change in changes:
            self._s.add(
                EtfHoldingChangeORM(
                    etf_id=etf.id,
                    as_of_date=change.as_of_date,
                    prev_date=change.prev_date,
                    holding_ticker=change.holding_ticker,
                    holding_name=change.holding_name,
                    change_type=change.change_type,
                    shares_before=change.shares_before,
                    shares_after=change.shares_after,
                    shares_delta=change.shares_delta,
                    shares_delta_pct=change.shares_delta_pct,
                    weight_before=change.weight_before,
                    weight_after=change.weight_after,
                    weight_delta=change.weight_delta,
                )
            )
        return len(changes)

    async def for_snapshot(
        self,
        ticker: str,
        *,
        as_of_date: date | None = None,
        include_unchanged: bool = False,
    ) -> list[HoldingChange]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        target_date = as_of_date or await self._latest_change_date(etf.id)
        if target_date is None:
            return []

        stmt = (
            select(EtfHoldingChangeORM)
            .options(selectinload(EtfHoldingChangeORM.etf))
            .where(
                EtfHoldingChangeORM.etf_id == etf.id,
                EtfHoldingChangeORM.as_of_date == target_date,
            )
        )
        if not include_unchanged:
            stmt = stmt.where(EtfHoldingChangeORM.change_type != ChangeType.UNCHANGED)

        rows = (
            await self._s.scalars(
                stmt.order_by(
                    EtfHoldingChangeORM.change_type.asc(),
                    func.abs(EtfHoldingChangeORM.weight_delta).desc().nullslast(),
                    func.abs(EtfHoldingChangeORM.shares_delta).desc().nullslast(),
                )
            )
        ).all()
        return [mappers.to_holding_change(row) for row in rows]

    async def for_position(self, ticker: str, holding: str) -> list[HoldingChange]:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(ticker)))
        if etf is None:
            return []

        target = holding if holding.startswith("NAME:") else holding_key(holding, "")
        rows = (
            await self._s.scalars(
                select(EtfHoldingChangeORM)
                .options(selectinload(EtfHoldingChangeORM.etf))
                .where(EtfHoldingChangeORM.etf_id == etf.id)
                .order_by(EtfHoldingChangeORM.as_of_date.asc())
            )
        ).all()
        return [
            mappers.to_holding_change(row)
            for row in rows
            if holding_key(row.holding_ticker, row.holding_name) == target
        ]

    async def recent(
        self,
        *,
        limit: int = 100,
        change_types: list[str] | None = None,
    ) -> list[HoldingChange]:
        stmt = select(EtfHoldingChangeORM).options(selectinload(EtfHoldingChangeORM.etf))
        if change_types:
            stmt = stmt.where(EtfHoldingChangeORM.change_type.in_(change_types))

        rows = (
            await self._s.scalars(
                stmt.order_by(EtfHoldingChangeORM.as_of_date.desc(), EtfHoldingChangeORM.id.desc())
                .limit(limit)
            )
        ).all()
        return [mappers.to_holding_change(row) for row in rows]

    async def _latest_change_date(self, etf_id: int) -> date | None:
        return await self._s.scalar(
            select(func.max(EtfHoldingChangeORM.as_of_date)).where(
                EtfHoldingChangeORM.etf_id == etf_id
            )
        )


class SqlAlchemyMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert(self, metric: Metric) -> None:
        etf = await self._s.scalar(select(EtfORM).where(EtfORM.ticker == normalize_ticker(metric.ticker)))
        if etf is None:
            return

        row = await self._s.scalar(select(EtfMetricORM).where(EtfMetricORM.etf_id == etf.id))
        if row is None:
            self._s.add(
                EtfMetricORM(
                    etf_id=etf.id,
                    as_of=metric.as_of,
                    aum=metric.aum,
                    return_1m=metric.return_1m,
                    return_3m=metric.return_3m,
                    return_ytd=metric.return_ytd,
                    return_1y=metric.return_1y,
                )
            )
            return

        row.as_of = metric.as_of
        row.aum = metric.aum
        row.return_1m = metric.return_1m
        row.return_3m = metric.return_3m
        row.return_ytd = metric.return_ytd
        row.return_1y = metric.return_1y

    async def get(self, ticker: str) -> Metric | None:
        row = await self._s.scalar(
            select(EtfMetricORM)
            .options(selectinload(EtfMetricORM.etf))
            .join(EtfORM)
            .where(EtfORM.ticker == normalize_ticker(ticker))
        )
        return mappers.to_metric(row) if row else None

    async def get_many(self, tickers: list[str]) -> dict[str, Metric]:
        if not tickers:
            return {}

        normalized = [normalize_ticker(ticker) for ticker in tickers]
        rows = (
            await self._s.scalars(
                select(EtfMetricORM)
                .options(selectinload(EtfMetricORM.etf))
                .join(EtfORM)
                .where(EtfORM.ticker.in_(normalized))
            )
        ).all()
        metrics = [mappers.to_metric(row) for row in rows]
        return {metric.ticker: metric for metric in metrics}


class SqlAlchemyCollectionRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def start(self, job_name: str) -> CollectionRun:
        row = CollectionRunORM(
            job_name=job_name,
            status="running",
            started_at=datetime.now(UTC),
            items_processed=0,
        )
        self._s.add(row)
        await self._s.flush()
        return mappers.to_collection_run(row)

    async def finish(
        self,
        run_id: int,
        *,
        status: str,
        items_processed: int,
        error: str | None = None,
    ) -> CollectionRun:
        row = await self._s.get(CollectionRunORM, run_id)
        if row is None:
            row = CollectionRunORM(
                id=run_id,
                job_name="unknown",
                status=status,
                started_at=datetime.now(UTC),
            )
            self._s.add(row)
        row.status = status
        row.finished_at = datetime.now(UTC)
        row.items_processed = items_processed
        row.error = error
        await self._s.flush()
        return mappers.to_collection_run(row)

    async def list_recent(self, *, limit: int = 20) -> list[CollectionRun]:
        rows = (
            await self._s.scalars(
                select(CollectionRunORM).order_by(CollectionRunORM.started_at.desc()).limit(limit)
            )
        ).all()
        return [mappers.to_collection_run(row) for row in rows]
