from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.application.services.metric_service import MetricService
from app.application.services.holding_change_service import HoldingChangeService
from app.domain.entities import Etf, Holding
from app.domain.value_objects import holding_key, normalize_ticker
from app.infrastructure.db.engine import SessionLocal
from app.infrastructure.db.repositories import (
    SqlAlchemyCollectionLockRepository,
    SqlAlchemyCollectionRunRepository,
    SqlAlchemyEtfRepository,
    SqlAlchemyHoldingChangeRepository,
    SqlAlchemyHoldingRepository,
    SqlAlchemyMetricRepository,
    SqlAlchemyPriceRepository,
)
from app.infrastructure.external.holdings.registry import HoldingsProviderRegistry
from app.infrastructure.external.universe import load_seed_universe
from app.infrastructure.external.yfinance_provider import YFinanceMarketDataProvider


COLLECTION_LOCK_KEY = "holdings_collect"


class CollectionAlreadyRunningError(RuntimeError):
    pass


async def collect_once(
    *,
    job_name: str = "manual_collect",
    lookback_days: int = 365,
    collect_prices: bool = False,
    collect_holdings: bool = True,
    lock_already_acquired: bool = False,
) -> int:
    async with collection_lock(already_acquired=lock_already_acquired):
        return await _collect_once_unlocked(
            job_name=job_name,
            lookback_days=lookback_days,
            collect_prices=collect_prices,
            collect_holdings=collect_holdings,
        )


async def acquire_collection_lock() -> bool:
    async with SessionLocal() as session:
        acquired = await SqlAlchemyCollectionLockRepository(session).acquire(COLLECTION_LOCK_KEY)
        await session.commit()
        return acquired


async def release_collection_lock() -> None:
    async with SessionLocal() as session:
        await SqlAlchemyCollectionLockRepository(session).release(COLLECTION_LOCK_KEY)
        await session.commit()


@asynccontextmanager
async def collection_lock(*, already_acquired: bool = False) -> AsyncIterator[None]:
    acquired = already_acquired
    if not acquired:
        acquired = await acquire_collection_lock()
        if not acquired:
            raise CollectionAlreadyRunningError("collection already running")
    try:
        yield
    finally:
        if acquired:
            await release_collection_lock()


async def _collect_once_unlocked(
    *,
    job_name: str,
    lookback_days: int,
    collect_prices: bool,
    collect_holdings: bool,
) -> int:
    async with SessionLocal() as session:
        etfs = SqlAlchemyEtfRepository(session)
        prices = SqlAlchemyPriceRepository(session)
        metrics = SqlAlchemyMetricRepository(session)
        holdings = SqlAlchemyHoldingRepository(session)
        changes = SqlAlchemyHoldingChangeRepository(session)
        runs = SqlAlchemyCollectionRunRepository(session)
        metric_service = MetricService()
        change_service = HoldingChangeService()
        price_provider = YFinanceMarketDataProvider()
        holdings_registry = HoldingsProviderRegistry()

        run = await runs.start(job_name)
        processed = 0
        errors: list[str] = []

        try:
            seeded = await load_seed_universe(etfs)
            processed += seeded
            await session.commit()

            universe, _ = await etfs.list(page=1, page_size=1000)
            for etf in universe:
                if collect_holdings:
                    holdings_provider = holdings_registry.provider_for(etf)
                    if holdings_provider is not None:
                        try:
                            fetched_holdings = await holdings_provider.fetch_holdings(etf)
                            fetched_holdings = prepare_holdings_batch(etf, fetched_holdings)
                            as_of = fetched_holdings[0].as_of_date
                            written_holdings = await holdings.upsert_many(fetched_holdings)
                            previous_date = await holdings.previous_snapshot_date(etf.ticker, as_of)
                            previous_holdings = (
                                await holdings.snapshot(etf.ticker, previous_date)
                                if previous_date is not None
                                else []
                            )
                            snapshot_changes = change_service.diff(
                                etf.ticker,
                                as_of,
                                previous_date,
                                fetched_holdings,
                                previous_holdings,
                            )
                            written_changes = await changes.upsert_many(snapshot_changes)
                            await session.commit()
                            processed += written_holdings + written_changes
                        except Exception as exc:  # noqa: BLE001 - partial collection should continue.
                            await session.rollback()
                            errors.append(f"{etf.ticker} holdings: {exc}")

                if collect_prices:
                    try:
                        fetched = await price_provider.fetch_prices(
                            etf.ticker, lookback_days=lookback_days
                        )
                        processed += await prices.upsert_many(fetched)
                        series = await prices.series(etf.ticker, range_="1y")
                        metric = metric_service.calculate(etf.ticker, series)
                        if metric is not None:
                            await metrics.upsert(metric)
                        await session.commit()
                    except Exception as exc:  # noqa: BLE001 - partial collection should continue.
                        await session.rollback()
                        errors.append(f"{etf.ticker} prices: {exc}")

            status = "partial" if errors and processed else "failed" if errors else "success"
            error = "\n".join(errors) if errors else None
            await runs.finish(run.id or 0, status=status, items_processed=processed, error=error)
            await session.commit()
            return processed
        except Exception as exc:
            await session.rollback()
            await runs.finish(
                run.id or 0, status="failed", items_processed=processed, error=str(exc)
            )
            await session.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect active ETF holdings snapshots and context data."
    )
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--with-prices", action="store_true")
    parser.add_argument("--skip-holdings", action="store_true")
    args = parser.parse_args()

    processed = asyncio.run(
        collect_once(
            job_name="manual_collect",
            lookback_days=args.lookback_days,
            collect_prices=args.with_prices and not args.seed_only,
            collect_holdings=not args.seed_only and not args.skip_holdings,
        )
    )
    print(f"processed={processed}")


def prepare_holdings_batch(etf: Etf, holdings: list[Holding]) -> list[Holding]:
    if not holdings:
        raise ValueError(f"{etf.ticker} returned no holdings")

    expected_ticker = normalize_ticker(etf.ticker)
    tickers = {normalize_ticker(holding.ticker) for holding in holdings}
    dates = {holding.as_of_date for holding in holdings}
    if tickers != {expected_ticker} or len(dates) != 1:
        raise ValueError(
            f"Invalid holdings batch for {expected_ticker}: "
            f"tickers={sorted(tickers)}, dates={sorted(dates)}"
        )

    prepared: dict[str, Holding] = {}
    order: list[str] = []
    for holding in holdings:
        key = holding_key(holding.holding_ticker, holding.holding_name, holding.security_id)
        if key is None or _is_zero_economic_row(holding):
            continue
        if holding.shares is None:
            raise ValueError(
                f"Missing shares for {expected_ticker} {holding.as_of_date} "
                f"{holding.holding_ticker or holding.holding_name}"
            )
        existing = prepared.get(key)
        if existing is None:
            prepared[key] = holding
            order.append(key)
            continue
        existing.weight += holding.weight
        existing.shares = _sum_required(existing.shares, holding.shares)
        existing.market_value = _sum_optional(existing.market_value, holding.market_value)

    if not prepared:
        raise ValueError(f"{expected_ticker} returned no material holdings")
    return [prepared[key] for key in order]


def _is_zero_economic_row(holding: Holding) -> bool:
    return (holding.shares or 0) == 0 and (holding.market_value or 0) == 0 and holding.weight == 0


def _sum_required(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        raise ValueError("Cannot aggregate holdings with missing shares")
    return left + right


def _sum_optional(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


if __name__ == "__main__":
    main()
