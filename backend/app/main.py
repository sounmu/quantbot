from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.services.universe_service import SignalUniversePolicy, refresh_signal_universe
from app.config import get_settings
from app.infrastructure.db.engine import SessionLocal, init_db
from app.infrastructure.db.repositories import SqlAlchemyEtfRepository, SqlAlchemyMetricRepository
from app.infrastructure.external.universe import load_seed_universe
from app.infrastructure.scheduler.jobs import create_scheduler
from app.interfaces.api import admin, analysis, changes, etfs, meta, signals


async def seed_universe() -> int:
    settings = get_settings()
    async with SessionLocal() as session:
        etfs = SqlAlchemyEtfRepository(session)
        metrics = SqlAlchemyMetricRepository(session)
        count = await load_seed_universe(etfs, metrics=metrics)
        await refresh_signal_universe(
            etfs,
            metrics,
            SignalUniversePolicy(
                min_aum=settings.signal_min_aum,
                exchanges=settings.signal_exchange_list,
            ),
        )
        await session.commit()
        return count


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler: AsyncIOScheduler | None = None

    if settings.auto_create_tables:
        await init_db()

    if settings.seed_universe_on_startup:
        await seed_universe()

    if settings.scheduler_enabled:
        scheduler = create_scheduler(settings)
        scheduler.start()

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Quantbot API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(etfs.router)
    app.include_router(changes.router)
    app.include_router(signals.router)
    app.include_router(analysis.router)
    app.include_router(meta.router)
    app.include_router(admin.router)
    return app


app = create_app()
