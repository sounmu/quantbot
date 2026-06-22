from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PricePointResponse(BaseModel):
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    nav: float | None = None
    volume: int | None = None

