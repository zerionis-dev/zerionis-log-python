"""Tests for concurrent context isolation."""

from __future__ import annotations

import asyncio

from zerionis_log.context import ZerionisContext


class TestConcurrentContextIsolation:
    async def test_concurrent_requests_isolated(self) -> None:
        """Multiple async tasks must not contaminate each other's context."""
        results: dict[str, str | None] = {}

        async def simulate_request(req_id: str) -> None:
            ZerionisContext.set(trace_id=f"trace-{req_id}", request_id=f"req-{req_id}")
            # Yield to let other tasks run
            await asyncio.sleep(0.01)
            ctx = ZerionisContext.get()
            results[req_id] = ctx.get("trace_id")
            ZerionisContext.clear()

        tasks = [simulate_request(f"r{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        for i in range(10):
            key = f"r{i}"
            assert results[key] == f"trace-{key}", f"Context leaked for {key}: got {results[key]}"

    async def test_nested_async_context(self) -> None:
        """Inner coroutine inherits context from parent task."""
        ZerionisContext.set(trace_id="parent-trace")

        async def inner() -> str | None:
            ctx = ZerionisContext.get()
            return ctx.get("trace_id")

        result = await inner()
        assert result == "parent-trace"
        ZerionisContext.clear()

    async def test_clear_does_not_affect_sibling(self) -> None:
        """Clearing in one task does not affect sibling tasks."""
        barrier = asyncio.Event()
        results: dict[str, str | None] = {}

        async def task_a() -> None:
            ZerionisContext.set(trace_id="trace-a")
            barrier.set()
            await asyncio.sleep(0.02)
            ctx = ZerionisContext.get()
            results["a"] = ctx.get("trace_id")
            ZerionisContext.clear()

        async def task_b() -> None:
            ZerionisContext.set(trace_id="trace-b")
            await barrier.wait()
            ZerionisContext.clear()
            await asyncio.sleep(0.01)
            results["b_after_clear"] = ZerionisContext.get().get("trace_id")

        await asyncio.gather(task_a(), task_b())
        # task_a's context should survive task_b's clear
        assert results["a"] == "trace-a"
        # task_b cleared its own context
        assert results["b_after_clear"] is None
