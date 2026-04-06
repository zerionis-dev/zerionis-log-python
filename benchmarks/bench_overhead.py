"""Benchmark: measure per-operation overhead of formatter and sanitizer."""

from __future__ import annotations

import logging
import time

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.formatter import ZerionisFormatter
from zerionis_log.sanitizer import Sanitizer

N = 10_000


def bench_formatter() -> None:
    cfg = ZerionisConfig(service_name="bench", environment="prod", version="1.0.0")
    fmt = ZerionisFormatter(cfg)

    ZerionisContext.set(trace_id="550e8400-e29b-41d4-a716-446655440000", request_id="req-abc123")

    record = logging.LogRecord(
        name="bench.test",
        level=logging.INFO,
        pathname="bench.py",
        lineno=1,
        msg="Benchmark log message with some content",
        args=(),
        exc_info=None,
    )

    # Warm up
    for _ in range(100):
        fmt.format(record)

    start = time.perf_counter()
    for _ in range(N):
        fmt.format(record)
    elapsed = time.perf_counter() - start

    per_op = (elapsed / N) * 1_000_000  # microseconds
    print(f"Formatter: {N} events in {elapsed:.3f}s = {per_op:.1f} us/event")
    ZerionisContext.clear()


def bench_sanitizer() -> None:
    s = Sanitizer(partial_redaction=True)
    payload = {
        "user": {
            "name": "Alice",
            "email": "alice@example.com",
            "password": "super_secret_password_1234",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.long.token",
        },
        "payment": {
            "card_number": "4111111111111111",
            "cvv": "123",
            "amount": 99.99,
        },
        "metadata": {
            "api_key": "sk-1234567890abcdef",
            "request_id": "req-abc123",
        },
    }

    # Warm up
    for _ in range(100):
        s.sanitize(payload)

    start = time.perf_counter()
    for _ in range(N):
        s.sanitize(payload)
    elapsed = time.perf_counter() - start

    per_op = (elapsed / N) * 1_000_000
    print(f"Sanitizer: {N} payloads in {elapsed:.3f}s = {per_op:.1f} us/payload")


if __name__ == "__main__":
    print(f"Running {N} iterations each...\n")
    bench_formatter()
    bench_sanitizer()
    print("\nDone.")
