from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Any


class TaskRunner:
    """Small backend task runner with separate fast and heavy thread pools."""

    def __init__(self, max_workers: int = 4, heavy_workers: int = 2):
        self._fast_executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="jarvis-fast",
        )
        self._heavy_executor = ThreadPoolExecutor(
            max_workers=heavy_workers,
            thread_name_prefix="jarvis-heavy",
        )
        self._executor = self._fast_executor
        self._closed = False

    def submit_fast(self, function: Callable[..., Any], *args, **kwargs) -> Future:
        if self._closed:
            raise RuntimeError("TaskRunner is already shut down")
        return self._fast_executor.submit(function, *args, **kwargs)

    def submit_heavy(self, function: Callable[..., Any], *args, **kwargs) -> Future:
        if self._closed:
            raise RuntimeError("TaskRunner is already shut down")
        return self._heavy_executor.submit(function, *args, **kwargs)

    def submit(self, function: Callable[..., Any], *args, **kwargs) -> Future:
        return self.submit_fast(function, *args, **kwargs)

    def shutdown(self, wait: bool = False, cancel_futures: bool = True) -> None:
        if self._closed:
            return
        self._closed = True
        self._fast_executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        self._heavy_executor.shutdown(wait=wait, cancel_futures=cancel_futures)
