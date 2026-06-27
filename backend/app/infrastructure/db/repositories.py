from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, delete, distinct, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import (
    CollectionItemLog,
    CollectionRun,
    Etf,
    Holding,
    HoldingChange,
    Metric,
    PricePoint,
    Security,
    SecurityPrice,
    SignalDaily,
    SignalOutcome,
    SignalParticipant,
)
from app.domain.value_objects import (
    ChangeType,
    SignalDirection,
    holding_key,
    normalize_security_key,
    normalize_ticker,
)
from app.infrastructure.db import mappers
from app.infrastructure.db.orm_models import (
    CollectionItemLogORM,
    CollectionLockORM,
    CollectionRunORM,
    EtfHoldingChangeORM,
    EtfHoldingORM,
    EtfMetricORM,
    EtfORM,
    EtfPriceORM,
    SecurityORM,
    SecurityPriceORM,
    SignalDailyORM,
    SignalOutcomeORM,
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
                    exchange=etf.exchange,
                    aum=etf.aum,
                    in_signal_universe=etf.in_signal_universe,
                    signal_universe_reason=etf.signal_universe_reason,
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
        row.exchange = etf.exchange
        row.aum = etf.aum
        row.in_signal_universe = etf.in_signal_universe
        row.signal_universe_reason = etf.signal_universe_reason
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

        stmt = stmt.order_by(
            sort_column.desc().nullslast() if order == "desc" else sort_column.asc()
        )
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
        if not prices:
            return 0

        prices_by_ticker: dict[str, list[PricePoint]] = {}
        for price in prices:
            prices_by_ticker.setdefault(normalize_ticker(price.ticker), []).append(price)

        etf_rows = (
            await self._s.scalars(select(EtfORM).where(EtfORM.ticker.in_(list(prices_by_ticker))))
        ).all()
        etfs_by_ticker = {etf.ticker: etf for etf in etf_rows}
        processed = 0
        for ticker, ticker_prices in prices_by_ticker.items():
            etf = etfs_by_ticker.get(ticker)
            if etf is None:
                continue

            dates = {price.on for price in ticker_prices}
            rows = (
                await self._s.scalars(
                    select(EtfPriceORM).where(
                        EtfPriceORM.etf_id == etf.id,
                        EtfPriceORM.date.in_(dates),
                    )
                )
            ).all()
            rows_by_date = {row.date: row for row in rows}

            for price in ticker_prices:
                row = rows_by_date.get(price.on)
                if row is None:
                    row = EtfPriceORM(
                        etf_id=etf.id,
                        date=price.on,
                        open=price.open,
                        high=price.high,
                        low=price.low,
                        close=price.close,
                        nav=price.nav,
                        volume=price.volume,
                    )
                    self._s.add(row)
                    rows_by_date[price.on] = row
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

        stmt = (
            select(EtfPriceORM)
            .options(selectinload(EtfPriceORM.etf))
            .where(EtfPriceORM.etf_id == etf.id)
        )
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


class SqlAlchemySecurityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, securities: list[Security]) -> int:
        if not securities:
            return 0

        processed = 0
        for security in securities:
            key = normalize_security_key(security.security_key)
            row = await self._s.get(SecurityORM, key)
            if row is None:
                self._s.add(
                    SecurityORM(
                        security_key=key,
                        ticker=normalize_ticker(security.ticker),
                        name=security.name,
                        first_seen=security.first_seen,
                        is_priceable=security.is_priceable,
                    )
                )
                processed += 1
                continue

            row.ticker = normalize_ticker(security.ticker)
            row.name = security.name
            row.first_seen = min(row.first_seen, security.first_seen)
            row.is_priceable = security.is_priceable
            processed += 1
        return processed

    async def get(self, security_key: str) -> Security | None:
        row = await self._s.get(SecurityORM, normalize_security_key(security_key))
        return mappers.to_security(row) if row else None

    async def list_priceable(self) -> list[Security]:
        rows = (
            await self._s.scalars(
                select(SecurityORM)
                .where(SecurityORM.is_priceable.is_(True))
                .order_by(SecurityORM.ticker.asc())
            )
        ).all()
        return [mappers.to_security(row) for row in rows]


class SqlAlchemySecurityPriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, prices: list[SecurityPrice]) -> int:
        if not prices:
            return 0

        prices_by_key: dict[str, list[SecurityPrice]] = {}
        for price in prices:
            prices_by_key.setdefault(normalize_security_key(price.security_key), []).append(price)

        existing_keys = set(
            (
                await self._s.scalars(
                    select(SecurityORM.security_key).where(
                        SecurityORM.security_key.in_(list(prices_by_key))
                    )
                )
            ).all()
        )
        processed = 0
        for security_key, key_prices in prices_by_key.items():
            if security_key not in existing_keys:
                continue

            dates = {price.on for price in key_prices}
            rows = (
                await self._s.scalars(
                    select(SecurityPriceORM).where(
                        SecurityPriceORM.security_key == security_key,
                        SecurityPriceORM.date.in_(dates),
                    )
                )
            ).all()
            rows_by_date = {row.date: row for row in rows}

            for price in key_prices:
                row = rows_by_date.get(price.on)
                if row is None:
                    row = SecurityPriceORM(
                        security_key=security_key,
                        date=price.on,
                        close=price.close,
                        adj_close=price.adj_close,
                        volume=price.volume,
                    )
                    self._s.add(row)
                    rows_by_date[price.on] = row
                else:
                    row.close = price.close
                    row.adj_close = price.adj_close
                    row.volume = price.volume
                processed += 1
        return processed

    async def series(self, security_key: str) -> list[SecurityPrice]:
        rows = (
            await self._s.scalars(
                select(SecurityPriceORM)
                .where(SecurityPriceORM.security_key == normalize_security_key(security_key))
                .order_by(SecurityPriceORM.date.asc())
            )
        ).all()
        return [mappers.to_security_price(row) for row in rows]

    async def latest_date(self, security_key: str) -> date | None:
        return await self._s.scalar(
            select(func.max(SecurityPriceORM.date)).where(
                SecurityPriceORM.security_key == normalize_security_key(security_key)
            )
        )

    async def latest_adj_close_by_security(
        self,
        security_keys: list[str],
        *,
        on_or_before: date,
    ) -> dict[str, float]:
        if not security_keys:
            return {}

        normalized_keys = [normalize_security_key(key) for key in security_keys]
        rows = (
            await self._s.scalars(
                select(SecurityPriceORM)
                .where(
                    SecurityPriceORM.security_key.in_(normalized_keys),
                    SecurityPriceORM.date <= on_or_before,
                )
                .order_by(SecurityPriceORM.security_key.asc(), SecurityPriceORM.date.desc())
            )
        ).all()

        prices: dict[str, float] = {}
        for row in rows:
            if row.security_key not in prices:
                prices[row.security_key] = row.adj_close
        return prices


class SqlAlchemySignalDailyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def replace_for_dates(self, dates: list[date], signals: list[SignalDaily]) -> int:
        target_dates = sorted(set(dates))
        if not target_dates:
            return 0

        await self._s.execute(
            delete(SignalDailyORM).where(SignalDailyORM.as_of_date.in_(target_dates))
        )
        for signal in signals:
            self._s.add(
                SignalDailyORM(
                    security_key=normalize_security_key(signal.security_key),
                    as_of_date=signal.as_of_date,
                    n_buying=signal.n_buying,
                    n_selling=signal.n_selling,
                    net_shares_flow=signal.net_shares_flow,
                    net_dollar_flow=signal.net_dollar_flow,
                    conviction_score=signal.conviction_score,
                )
            )
        return len(signals)

    async def latest_date(self) -> date | None:
        return await self._s.scalar(select(func.max(SignalDailyORM.as_of_date)))

    async def daily(
        self,
        *,
        as_of_date: date | None = None,
        limit: int = 100,
    ) -> list[SignalDaily]:
        target_date = as_of_date or await self.latest_date()
        if target_date is None:
            return []

        rows = (
            await self._s.scalars(
                select(SignalDailyORM)
                .options(selectinload(SignalDailyORM.security))
                .where(SignalDailyORM.as_of_date == target_date)
                .order_by(
                    SignalDailyORM.conviction_score.desc(),
                    func.abs(SignalDailyORM.net_dollar_flow).desc().nullslast(),
                    func.abs(SignalDailyORM.net_shares_flow).desc().nullslast(),
                    SignalDailyORM.security_key.asc(),
                )
                .limit(limit)
            )
        ).all()
        return [mappers.to_signal_daily(row) for row in rows]

    async def for_security(self, security_key: str, *, limit: int = 100) -> list[SignalDaily]:
        rows = (
            await self._s.scalars(
                select(SignalDailyORM)
                .options(selectinload(SignalDailyORM.security))
                .where(SignalDailyORM.security_key == normalize_security_key(security_key))
                .order_by(SignalDailyORM.as_of_date.desc())
                .limit(limit)
            )
        ).all()
        return [mappers.to_signal_daily(row) for row in rows]

    async def buy_signals(self) -> list[SignalDaily]:
        rows = (
            await self._s.scalars(
                select(SignalDailyORM)
                .options(selectinload(SignalDailyORM.security))
                .where(SignalDailyORM.conviction_score > 0)
                .order_by(SignalDailyORM.as_of_date.asc(), SignalDailyORM.security_key.asc())
            )
        ).all()
        return [mappers.to_signal_daily(row) for row in rows]


class SqlAlchemySignalOutcomeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def replace_all(self, outcomes: list[SignalOutcome]) -> int:
        await self._s.execute(delete(SignalOutcomeORM))
        for outcome in outcomes:
            self._s.add(
                SignalOutcomeORM(
                    security_key=normalize_security_key(outcome.security_key),
                    as_of_date=outcome.as_of_date,
                    horizon_days=outcome.horizon_days,
                    benchmark_key=normalize_security_key(outcome.benchmark_key),
                    start_date=outcome.start_date,
                    end_date=outcome.end_date,
                    stock_return=outcome.stock_return,
                    benchmark_return=outcome.benchmark_return,
                    excess_return=outcome.excess_return,
                    signal_score=outcome.signal_score,
                )
            )
        return len(outcomes)

    async def list(
        self,
        *,
        horizon_days: int | None = None,
        security_key: str | None = None,
    ) -> list[SignalOutcome]:
        stmt = select(SignalOutcomeORM)
        if horizon_days is not None:
            stmt = stmt.where(SignalOutcomeORM.horizon_days == horizon_days)
        if security_key is not None:
            stmt = stmt.where(SignalOutcomeORM.security_key == normalize_security_key(security_key))

        rows = (
            await self._s.scalars(
                stmt.order_by(
                    SignalOutcomeORM.as_of_date.desc(),
                    SignalOutcomeORM.horizon_days.asc(),
                    SignalOutcomeORM.security_key.asc(),
                )
            )
        ).all()
        return [mappers.to_signal_outcome(row) for row in rows]


class SqlAlchemyHoldingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, holdings: list[Holding]) -> int:
        if not holdings:
            return 0
        holdings = _prepare_holding_batch(holdings)

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
            key = holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
            if key is None:
                continue
            self._s.add(
                EtfHoldingORM(
                    etf_id=etf.id,
                    as_of_date=holding.as_of_date,
                    holding_key=key,
                    holding_ticker=holding.holding_ticker,
                    security_id=holding.security_id,
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

        target = _position_target(holding)
        if target is None:
            return []
        rows = (
            await self._s.scalars(
                select(EtfHoldingORM)
                .options(selectinload(EtfHoldingORM.etf))
                .where(EtfHoldingORM.etf_id == etf.id, EtfHoldingORM.holding_key == target)
                .order_by(EtfHoldingORM.as_of_date.asc())
            )
        ).all()
        return [mappers.to_holding(row) for row in rows]


class SqlAlchemyHoldingChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_many(self, changes: list[HoldingChange]) -> int:
        if not changes:
            return 0
        changes = _prepare_change_batch(changes)

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
            key = holding_key(change.holding_ticker, change.holding_name, change.security_id)
            if key is None:
                continue
            self._s.add(
                EtfHoldingChangeORM(
                    etf_id=etf.id,
                    as_of_date=change.as_of_date,
                    prev_date=change.prev_date,
                    holding_key=key,
                    holding_ticker=change.holding_ticker,
                    security_id=change.security_id,
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

        target = _position_target(holding)
        if target is None:
            return []
        rows = (
            await self._s.scalars(
                select(EtfHoldingChangeORM)
                .options(selectinload(EtfHoldingChangeORM.etf))
                .where(
                    EtfHoldingChangeORM.etf_id == etf.id, EtfHoldingChangeORM.holding_key == target
                )
                .order_by(EtfHoldingChangeORM.as_of_date.asc())
            )
        ).all()
        return [mappers.to_holding_change(row) for row in rows]

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
                stmt.order_by(
                    EtfHoldingChangeORM.as_of_date.desc(), EtfHoldingChangeORM.id.desc()
                ).limit(limit)
            )
        ).all()
        return [mappers.to_holding_change(row) for row in rows]

    async def signal_sources(self, *, as_of_date: date | None = None) -> list[HoldingChange]:
        stmt = (
            select(EtfHoldingChangeORM)
            .options(selectinload(EtfHoldingChangeORM.etf))
            .join(EtfORM, EtfORM.id == EtfHoldingChangeORM.etf_id)
            .join(SecurityORM, SecurityORM.security_key == EtfHoldingChangeORM.holding_key)
            .where(
                EtfORM.in_signal_universe.is_(True),
                EtfHoldingChangeORM.change_type.in_(_SIGNAL_CHANGE_TYPES),
                SecurityORM.is_priceable.is_(True),
            )
        )
        if as_of_date is not None:
            stmt = stmt.where(EtfHoldingChangeORM.as_of_date == as_of_date)

        rows = (
            await self._s.scalars(
                stmt.order_by(
                    EtfHoldingChangeORM.as_of_date.asc(),
                    EtfHoldingChangeORM.holding_key.asc(),
                    EtfORM.ticker.asc(),
                )
            )
        ).all()
        return [mappers.to_holding_change(row) for row in rows]

    async def signal_participants(
        self,
        security_key: str,
        *,
        as_of_date: date | None = None,
    ) -> list[SignalParticipant]:
        stmt = (
            select(EtfHoldingChangeORM)
            .options(selectinload(EtfHoldingChangeORM.etf))
            .join(EtfORM, EtfORM.id == EtfHoldingChangeORM.etf_id)
            .where(
                EtfORM.in_signal_universe.is_(True),
                EtfHoldingChangeORM.holding_key == normalize_security_key(security_key),
                EtfHoldingChangeORM.change_type.in_(_SIGNAL_CHANGE_TYPES),
            )
        )
        if as_of_date is not None:
            stmt = stmt.where(EtfHoldingChangeORM.as_of_date == as_of_date)

        rows = (
            await self._s.scalars(
                stmt.order_by(EtfHoldingChangeORM.as_of_date.desc(), EtfORM.ticker.asc())
            )
        ).all()
        return [_to_signal_participant(row) for row in rows]

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
        etf = await self._s.scalar(
            select(EtfORM).where(EtfORM.ticker == normalize_ticker(metric.ticker))
        )
        if etf is None:
            return
        if metric.aum is not None:
            etf.aum = metric.aum

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
        if metric.aum is not None:
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


class SqlAlchemyCollectionLockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def acquire(self, lock_key: str, *, stale_after_seconds: int = 7200) -> bool:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=stale_after_seconds)
        # 기존 행을 SELECT ... FOR UPDATE 로 잠근다. Postgres에서는 동시 acquire가 이
        # 행 잠금을 기다렸다가(우리가 commit 한 뒤) 갱신된 행을 다시 읽고 False 를
        # 반환하므로 read-check-write 사이의 TOCTOU 경쟁이 사라진다. 행 잠금을 잡고
        # 있는 동안에는 stale 행을 그대로 in-place UPDATE 해도 안전하다.
        # (SQLite 는 FOR UPDATE 를 무시하지만 DB 단위 쓰기 직렬화로 동등하게 보호된다.)
        row = await self._s.scalar(
            select(CollectionLockORM)
            .where(CollectionLockORM.lock_key == lock_key)
            .with_for_update()
        )
        if row is not None:
            if _aware_utc(row.acquired_at) > stale_before:
                return False
            row.acquired_at = now
            await self._s.flush()
            return True
        # 행이 아직 없으면 INSERT 경쟁이며, 패자는 PK unique 제약(IntegrityError)에 걸린다.
        self._s.add(CollectionLockORM(lock_key=lock_key, acquired_at=now))
        try:
            await self._s.flush()
        except IntegrityError:
            await self._s.rollback()
            return False
        return True

    async def release(self, lock_key: str) -> None:
        await self._s.execute(
            delete(CollectionLockORM).where(CollectionLockORM.lock_key == lock_key)
        )
        await self._s.flush()


def _prepare_holding_batch(holdings: list[Holding]) -> list[Holding]:
    _validate_single_holding_batch(holdings)
    merged: dict[str, Holding] = {}
    order: list[str] = []
    for holding in holdings:
        key = holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
        if key is None:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = holding
            order.append(key)
            continue
        existing.weight += holding.weight
        existing.shares = _sum_optional(existing.shares, holding.shares)
        existing.market_value = _sum_optional(existing.market_value, holding.market_value)
    return [merged[key] for key in order]


def _prepare_change_batch(changes: list[HoldingChange]) -> list[HoldingChange]:
    tickers = {normalize_ticker(change.ticker) for change in changes}
    dates = {change.as_of_date for change in changes}
    if len(tickers) != 1 or len(dates) != 1:
        raise ValueError(
            f"Mixed holding change batch: tickers={sorted(tickers)}, dates={sorted(dates)}"
        )
    seen: set[str] = set()
    prepared: list[HoldingChange] = []
    for change in changes:
        key = holding_key(change.holding_ticker, change.holding_name, change.security_id)
        if key is None:
            continue
        if key in seen:
            raise ValueError(f"Duplicate holding change key in batch: {key}")
        seen.add(key)
        prepared.append(change)
    return prepared


def _validate_single_holding_batch(holdings: list[Holding]) -> None:
    tickers = {normalize_ticker(holding.ticker) for holding in holdings}
    dates = {holding.as_of_date for holding in holdings}
    if len(tickers) != 1 or len(dates) != 1:
        raise ValueError(f"Mixed holdings batch: tickers={sorted(tickers)}, dates={sorted(dates)}")


def _sum_optional(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _position_target(holding: str) -> str | None:
    # The frontend sends back the canonical holding_key from the snapshot response
    # ("ID:..." / "NAME:..."); legacy/bare ticker values are normalized to their key.
    if holding.startswith(("NAME:", "ID:")):
        return holding
    return holding_key(holding, "")


_SIGNAL_CHANGE_TYPES = [
    ChangeType.NEW,
    ChangeType.INCREASE,
    ChangeType.EXIT,
    ChangeType.DECREASE,
]


def _to_signal_participant(row: EtfHoldingChangeORM) -> SignalParticipant:
    direction = (
        SignalDirection.BUY
        if row.change_type in {ChangeType.NEW, ChangeType.INCREASE}
        else SignalDirection.SELL
    )
    return SignalParticipant(
        etf_ticker=row.etf.ticker,
        etf_name=row.etf.name,
        issuer=row.etf.issuer,
        direction=direction,
        change_type=row.change_type,
        shares_delta=row.shares_delta,
        shares_delta_pct=row.shares_delta_pct,
        weight_delta=row.weight_delta,
    )


class SqlAlchemyCollectionItemLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def log_start(
        self,
        run_id: int,
        ticker: str,
        item_type: str,
        *,
        etf_id: int | None = None,
    ) -> CollectionItemLog:
        row = CollectionItemLogORM(
            run_id=run_id,
            etf_id=etf_id,
            ticker=ticker,
            item_type=item_type,
            status="running",
            row_count=0,
            started_at=datetime.now(UTC),
        )
        self._s.add(row)
        # Commit immediately so the audit record is durable before the work it
        # logs runs. Otherwise a session.rollback() of a failed item would erase
        # this row and the failure log would lose its ticker/run linkage.
        await self._s.commit()
        return mappers.to_collection_item_log(row)

    async def log_finish(
        self,
        log_id: int,
        *,
        status: str,
        row_count: int = 0,
        error: str | None = None,
    ) -> CollectionItemLog | None:
        row = await self._s.get(CollectionItemLogORM, log_id)
        if row is None:
            return None
        row.status = status
        row.row_count = row_count
        row.error = error
        row.finished_at = datetime.now(UTC)
        await self._s.commit()
        return mappers.to_collection_item_log(row)

    async def for_run(self, run_id: int) -> list[CollectionItemLog]:
        rows = (
            await self._s.scalars(
                select(CollectionItemLogORM)
                .where(CollectionItemLogORM.run_id == run_id)
                .order_by(CollectionItemLogORM.ticker, CollectionItemLogORM.item_type)
            )
        ).all()
        return [mappers.to_collection_item_log(row) for row in rows]


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
