from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.evaluation_service import EvaluationService
from app.application.services.etf_service import EtfService
from app.application.services.flow_service import FlowService
from app.application.services.metric_service import MetricService
from app.application.services.signal_service import SignalService
from app.infrastructure.db.engine import get_session
from app.infrastructure.db.repositories import (
    SqlAlchemyEtfRepository,
    SqlAlchemyEtfFlowRepository,
    SqlAlchemyHoldingChangeRepository,
    SqlAlchemyHoldingRepository,
    SqlAlchemyMetricRepository,
    SqlAlchemyPriceRepository,
    SqlAlchemySecurityPriceRepository,
    SqlAlchemySignalDailyRepository,
    SqlAlchemySignalOutcomeRepository,
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


def get_signal_service(session: AsyncSession = Depends(get_session)) -> SignalService:
    return SignalService(
        changes=SqlAlchemyHoldingChangeRepository(session),
        security_prices=SqlAlchemySecurityPriceRepository(session),
        signals=SqlAlchemySignalDailyRepository(session),
    )


def get_flow_service(session: AsyncSession = Depends(get_session)) -> FlowService:
    return FlowService(
        holdings=SqlAlchemyHoldingRepository(session),
        flows=SqlAlchemyEtfFlowRepository(session),
    )


def get_evaluation_service(session: AsyncSession = Depends(get_session)) -> EvaluationService:
    return EvaluationService(
        signals=SqlAlchemySignalDailyRepository(session),
        security_prices=SqlAlchemySecurityPriceRepository(session),
        outcomes=SqlAlchemySignalOutcomeRepository(session),
    )
