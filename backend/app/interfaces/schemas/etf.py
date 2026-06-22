from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EtfListItem(BaseModel):
    ticker: str
    name: str
    issuer: str
    theme: str | None = None
    expense_ratio: float | None = None
    discloses_daily: bool = True
    return_1m: float | None = None
    return_3m: float | None = None
    return_ytd: float | None = None
    return_1y: float | None = None


class EtfListResponse(BaseModel):
    items: list[EtfListItem]
    total: int
    page: int
    page_size: int


class EtfDetailResponse(EtfListItem):
    model_config = ConfigDict(from_attributes=True)

    inception_date: date | None = None
    currency: str = "USD"
    description: str | None = None
    as_of: date | None = None
    aum: float | None = None


class CompareItem(EtfListItem):
    as_of: date | None = None
    aum: float | None = None


class CompareResponse(BaseModel):
    items: list[CompareItem]
    series: dict[str, list[dict[str, float | str]]]
