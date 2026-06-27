from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.services.evaluation_service import (
    DEFAULT_HORIZONS,
    PERFORMANCE_BUCKETS,
    EvaluationService,
    PerformanceSummary,
    SecurityAnalysisPoint,
)
from app.interfaces.deps import get_evaluation_service
from app.interfaces.schemas.analysis import (
    PerformanceSummaryResponse,
    SecurityAnalysisPointResponse,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/performance", response_model=list[PerformanceSummaryResponse])
async def performance(
    bucket: str | None = Query(default=None, pattern=f"^({'|'.join(PERFORMANCE_BUCKETS)})$"),
    horizon: int | None = Query(default=None),
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[PerformanceSummaryResponse]:
    if horizon is not None and horizon not in DEFAULT_HORIZONS:
        raise HTTPException(status_code=422, detail="horizon must be one of 1, 5, 20, 60")
    summaries = await service.performance(bucket=bucket, horizon_days=horizon)
    return [_to_performance_response(summary) for summary in summaries]


@router.get("/security/{security_key:path}", response_model=list[SecurityAnalysisPointResponse])
async def security_analysis(
    security_key: str,
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[SecurityAnalysisPointResponse]:
    points = await service.security(security_key)
    return [_to_security_point_response(point) for point in points]


def _to_performance_response(summary: PerformanceSummary) -> PerformanceSummaryResponse:
    return PerformanceSummaryResponse(
        bucket=summary.bucket,
        horizon_days=summary.horizon_days,
        sample_size=summary.sample_size,
        hit_rate=summary.hit_rate,
        average_excess_return=summary.average_excess_return,
        median_excess_return=summary.median_excess_return,
        information_coefficient=summary.information_coefficient,
    )


def _to_security_point_response(
    point: SecurityAnalysisPoint,
) -> SecurityAnalysisPointResponse:
    return SecurityAnalysisPointResponse(
        as_of_date=point.as_of_date,
        horizon_days=point.horizon_days,
        start_date=point.start_date,
        end_date=point.end_date,
        stock_return=point.stock_return,
        benchmark_return=point.benchmark_return,
        excess_return=point.excess_return,
        signal_score=point.signal_score,
    )
