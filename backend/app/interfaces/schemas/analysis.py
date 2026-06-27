from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PerformanceSummaryResponse(BaseModel):
    bucket: str
    horizon_days: int
    sample_size: int
    hit_rate: float | None = None
    average_excess_return: float | None = None
    median_excess_return: float | None = None
    information_coefficient: float | None = None


class SecurityAnalysisPointResponse(BaseModel):
    as_of_date: date
    horizon_days: int
    start_date: date
    end_date: date
    stock_return: float
    benchmark_return: float
    excess_return: float
    signal_score: float
