"""Async singleflight helper: ensure only one in-flight coroutine runs and others await its result.

This is intentionally small and dependency-free so desktop apps can await a single
in-flight refresh without writing complex coordination code.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Coroutine


class AsyncSingleflight:
    """Coordinate a single in-flight async operation.

    Usage:
        sf = AsyncSingleflight()
        result = await sf.do(lambda: some_coro())
    If a caller invokes `do` while an operation is already in flight, they will
    await the same task and receive the same result or exception.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task[Any]] = None

    async def do(self, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
        # Ensure only one Task is created; callers share the task.
        async with self._lock:
            if self._task is None:
                self._task = asyncio.create_task(coro_factory())
            task = self._task

        try:
            return await task
        finally:
            # Clear the task once it's done so a subsequent call will re-run.
            async with self._lock:
                if self._task is task and task.done():
                    self._task = None
