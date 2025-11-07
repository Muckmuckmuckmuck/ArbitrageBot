from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Deque, Optional, Tuple

from collections import deque


class TokenBucket:
    """Simple token bucket implementation for rate limiting."""

    def __init__(self, capacity: float, refill_rate_per_sec: float) -> None:
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate_per_sec
        self.last_refill = time.perf_counter()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: float = 1.0) -> None:
        async with self._lock:
            await self._await_capacity(tokens)
            self.tokens -= tokens

    async def _await_capacity(self, tokens: float) -> None:
        while self.tokens < tokens:
            self._refill()
            if self.tokens >= tokens:
                break
            sleep_for = (tokens - self.tokens) / self.refill_rate
            await asyncio.sleep(max(sleep_for, 0.01))
        self._refill()

    def _refill(self) -> None:
        now = time.perf_counter()
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


TaskCallable = Callable[[], Awaitable[Any]]


@dataclass
class RateLimitedTask:
    priority: int
    coro_factory: TaskCallable
    description: str = ""


class RateLimitedExecutor:
    """Priority-aware executor that respects a shared token bucket."""

    def __init__(self, bucket: TokenBucket, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.bucket = bucket
        self.loop = loop or asyncio.get_event_loop()
        self._queue: Deque[RateLimitedTask] = deque()
        self._is_running = False
        self._condition = asyncio.Condition()

    async def submit(self, task: RateLimitedTask, tokens: float = 1.0) -> Any:
        async with self._condition:
            self._insert_task(task)
            self._condition.notify()

        fut = self.loop.create_future()

        async def wrapped() -> None:
            try:
                await self.bucket.consume(tokens)
                result = await task.coro_factory()
                fut.set_result(result)
            except Exception as exc:  # noqa: BLE001
                fut.set_exception(exc)

        self.loop.create_task(wrapped())
        return await fut

    def _insert_task(self, task: RateLimitedTask) -> None:
        index = 0
        for existing in self._queue:
            if task.priority < existing.priority:
                break
            index += 1
        self._queue.insert(index, task)

    async def run(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        try:
            while True:
                async with self._condition:
                    while not self._queue:
                        await self._condition.wait()
                    task = self._queue.popleft()
                await self.bucket.consume()
                await task.coro_factory()
        finally:
            self._is_running = False

