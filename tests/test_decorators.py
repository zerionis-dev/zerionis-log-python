"""Tests for the @log_slow decorator."""

from __future__ import annotations

import time

import pytest

from zerionis_log.decorators import log_slow


class TestSyncDecorator:
    def test_fast_function_no_log(self) -> None:
        @log_slow(threshold_ms=1000)
        def fast() -> str:
            return "done"

        assert fast() == "done"

    def test_slow_function(self) -> None:
        @log_slow(threshold_ms=1)
        def slow() -> str:
            time.sleep(0.01)
            return "done"

        assert slow() == "done"

    def test_error_capture(self) -> None:
        @log_slow(threshold_ms=1000)
        def boom() -> None:
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            boom()

    def test_exclude_args(self) -> None:
        @log_slow(threshold_ms=1, exclude_args=["password"])
        def login(user: str, password: str) -> str:
            time.sleep(0.01)
            return user

        assert login("alice", "secret") == "alice"


class TestAsyncDecorator:
    async def test_fast_async(self) -> None:
        @log_slow(threshold_ms=1000)
        async def fast() -> str:
            return "done"

        assert await fast() == "done"

    async def test_slow_async(self) -> None:
        import asyncio

        @log_slow(threshold_ms=1)
        async def slow() -> str:
            await asyncio.sleep(0.01)
            return "done"

        assert await slow() == "done"

    async def test_async_error(self) -> None:
        @log_slow(threshold_ms=1000)
        async def boom() -> None:
            raise ValueError("async boom")

        with pytest.raises(ValueError, match="async boom"):
            await boom()

    async def test_async_exclude_args(self) -> None:
        import asyncio

        @log_slow(threshold_ms=1, exclude_args=["secret"])
        async def process(data: str, secret: str) -> str:
            await asyncio.sleep(0.01)
            return data

        assert await process("hello", "hidden") == "hello"
