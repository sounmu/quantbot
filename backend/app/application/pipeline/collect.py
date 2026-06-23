from __future__ import annotations

import argparse
import asyncio

from app.application.services.metric_service import MetricService
from app.application.services.holding_change_service import HoldingChangeService
from app.infrastructure.db.engine import SessionLocal
from app.infrastructure.db.repositories import (
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


async def collect_once(
    *,
    job_name: str = "manual_collect",
    lookback_days: int = 365,
    collect_prices: bool = False,
    collect_holdings: bool = True,
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
                            if fetched_holdings:
                                as_of = fetched_holdings[0].as_of_date
                                processed += await holdings.upsert_many(fetched_holdings)
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
                                processed += await changes.upsert_many(snapshot_changes)
                            await session.commit()
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
            await runs.finish(run.id or 0, status="failed", items_processed=processed, error=str(exc))
            await session.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect active ETF holdings snapshots and context data.")
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


if __name__ == "__main__":
    main()
