from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.entities import (
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
from app.domain.value_objects import ChangeType, SignalDirection, holding_key


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


class FakeSecurityRepository:
    def __init__(self) -> None:
        self._store: dict[str, Security] = {}

    async def upsert_many(self, securities: list[Security]) -> int:
        for security in securities:
            existing = self._store.get(security.security_key)
            if existing is not None and existing.first_seen < security.first_seen:
                security.first_seen = existing.first_seen
            self._store[security.security_key] = security
        return len(securities)

    async def get(self, security_key: str) -> Security | None:
        return self._store.get(security_key)

    async def list_priceable(self) -> list[Security]:
        return sorted(
            [security for security in self._store.values() if security.is_priceable],
            key=lambda security: security.ticker,
        )


class FakeSecurityPriceRepository:
    def __init__(self) -> None:
        self._store: dict[str, list[SecurityPrice]] = {}

    async def upsert_many(self, prices: list[SecurityPrice]) -> int:
        for price in prices:
            series = self._store.setdefault(price.security_key, [])
            series[:] = [existing for existing in series if existing.on != price.on]
            series.append(price)
        return len(prices)

    async def series(self, security_key: str) -> list[SecurityPrice]:
        return sorted(self._store.get(security_key, []), key=lambda point: point.on)

    async def latest_date(self, security_key: str) -> date | None:
        dates = {price.on for price in self._store.get(security_key, [])}
        return max(dates) if dates else None

    async def latest_adj_close_by_security(
        self,
        security_keys: list[str],
        *,
        on_or_before: date,
    ) -> dict[str, float]:
        result: dict[str, float] = {}
        for key in security_keys:
            eligible = [
                price for price in self._store.get(key, []) if price.on <= on_or_before
            ]
            if eligible:
                result[key] = max(eligible, key=lambda price: price.on).adj_close
        return result


class FakeSignalDailyRepository:
    def __init__(self) -> None:
        self._store: dict[tuple[str, date], SignalDaily] = {}

    async def replace_for_dates(self, dates: list[date], signals: list[SignalDaily]) -> int:
        target_dates = set(dates)
        self._store = {
            key: value for key, value in self._store.items() if value.as_of_date not in target_dates
        }
        for signal in signals:
            self._store[(signal.security_key, signal.as_of_date)] = signal
        return len(signals)

    async def latest_date(self) -> date | None:
        dates = {signal.as_of_date for signal in self._store.values()}
        return max(dates) if dates else None

    async def daily(
        self,
        *,
        as_of_date: date | None = None,
        limit: int = 100,
    ) -> list[SignalDaily]:
        target_date = as_of_date or await self.latest_date()
        if target_date is None:
            return []
        signals = [
            signal for signal in self._store.values() if signal.as_of_date == target_date
        ]
        return sorted(signals, key=lambda signal: signal.conviction_score, reverse=True)[:limit]

    async def for_security(self, security_key: str, *, limit: int = 100) -> list[SignalDaily]:
        signals = [
            signal for signal in self._store.values() if signal.security_key == security_key
        ]
        return sorted(signals, key=lambda signal: signal.as_of_date, reverse=True)[:limit]

    async def buy_signals(self) -> list[SignalDaily]:
        return sorted(
            [signal for signal in self._store.values() if signal.conviction_score > 0],
            key=lambda signal: (signal.as_of_date, signal.security_key),
        )


class FakeSignalOutcomeRepository:
    def __init__(self) -> None:
        self._store: list[SignalOutcome] = []

    async def replace_all(self, outcomes: list[SignalOutcome]) -> int:
        self._store = outcomes
        return len(outcomes)

    async def list(
        self,
        *,
        horizon_days: int | None = None,
        security_key: str | None = None,
    ) -> list[SignalOutcome]:
        outcomes = self._store
        if horizon_days is not None:
            outcomes = [outcome for outcome in outcomes if outcome.horizon_days == horizon_days]
        if security_key is not None:
            outcomes = [outcome for outcome in outcomes if outcome.security_key == security_key]
        return sorted(outcomes, key=lambda outcome: (outcome.as_of_date, outcome.horizon_days))


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

    async def signal_sources(self, *, as_of_date: date | None = None) -> list[HoldingChange]:
        signal_types = {ChangeType.NEW, ChangeType.INCREASE, ChangeType.EXIT, ChangeType.DECREASE}
        changes = [
            change
            for stored in self._store.values()
            for change in stored
            if change.change_type in signal_types
        ]
        if as_of_date is not None:
            changes = [change for change in changes if change.as_of_date == as_of_date]
        return sorted(changes, key=lambda change: (change.as_of_date, change.ticker))

    async def signal_participants(
        self,
        security_key: str,
        *,
        as_of_date: date | None = None,
    ) -> list[SignalParticipant]:
        participants: list[SignalParticipant] = []
        for change in await self.signal_sources(as_of_date=as_of_date):
            if holding_key(change.holding_ticker, change.holding_name, change.security_id) != security_key:
                continue
            direction = (
                SignalDirection.BUY
                if change.change_type in {ChangeType.NEW, ChangeType.INCREASE}
                else SignalDirection.SELL
            )
            participants.append(
                SignalParticipant(
                    etf_ticker=change.ticker,
                    etf_name=f"{change.ticker} ETF",
                    issuer="Test",
                    direction=direction,
                    change_type=change.change_type,
                    shares_delta=change.shares_delta,
                    shares_delta_pct=change.shares_delta_pct,
                    weight_delta=change.weight_delta,
                )
            )
        return participants


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
