from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.etf_service import EtfService
from app.application.services.metric_service import MetricService
from app.infrastructure.db.engine import get_session
from app.infrastructure.db.repositories import (
    SqlAlchemyEtfRepository,
    SqlAlchemyHoldingChangeRepository,
    SqlAlchemyHoldingRepository,
    SqlAlchemyMetricRepository,
    SqlAlchemyPriceRepository,
)


def get_etf_service(session: AsyncSession = Depends(get_session)) -> EtfService:
    return EtfService(
        etfs=SqlAlchemyEtfRepository(session),
        prices=SqlAlchemyPriceRepository(session),
        holdings=SqlAlchemyHoldingRepository(session),
        changes=SqlAlchemyHoldingChangeRepository(session),
        metrics=SqlAlchemyMetricRepository(session),
        metric_service=MetricService(),
    )
