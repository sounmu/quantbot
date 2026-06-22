from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CollectionRunResponse(BaseModel):
    id: int | None
    job_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    items_processed: int
    error: str | None = None

