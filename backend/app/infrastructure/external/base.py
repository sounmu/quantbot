from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class ExternalProviderError(RuntimeError):
    pass


async def with_backoff(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay_seconds: float = 0.5,
) -> T:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001 - normalize provider failures at boundary.
            last_error = exc
            if attempt < retries - 1:
                await asyncio.sleep(base_delay_seconds * (2**attempt))

    raise ExternalProviderError(str(last_error)) from last_error
