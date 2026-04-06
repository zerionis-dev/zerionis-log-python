"""Tests for the structured JSON formatter."""

from __future__ import annotations

import json
import logging

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.formatter import ZerionisFormatter
from zerionis_log.models import (
    EventType,
    HttpInfo,
    ServiceInfo,
    ZerionisLogEvent,
)


def _make_record(msg: str = "hello", level: int = logging.INFO, name: str = "test") -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def _format(record: logging.LogRecord, config: ZerionisConfig | None = None) -> dict:
    cfg = config or ZerionisConfig(service_name="test-svc", environment="test", version="1.0.0")
    fmt = ZerionisFormatter(cfg)
    raw = fmt.format(record)
    return json.loads(raw)


class TestFormatterBasic:
    def test_json_output_shape(self) -> None:
        data = _format(_make_record("hello world"))
        assert data["schema_version"] == "1.0"
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert data["event_type"] == "APPLICATION_LOG"
        assert data["service"]["name"] == "test-svc"
        assert "timestamp" in data

    def test_null_fields_omitted(self) -> None:
        data = _format(_make_record())
        assert "http" not in data
        assert "error" not in data
        assert "sql" not in data
        assert "user_id" not in data
        assert "duration_ms" not in data

    def test_error_level_sets_application_error(self) -> None:
        data = _format(_make_record(level=logging.ERROR))
        assert data["event_type"] == "APPLICATION_ERROR"

    def test_context_included(self) -> None:
        ZerionisContext.set(trace_id="550e8400-e29b-41d4-a716-446655440000", request_id="req-abc123")
        try:
            data = _format(_make_record())
            assert data["trace_id"] == "550e8400-e29b-41d4-a716-446655440000"
            assert data["request_id"] == "req-abc123"
        finally:
            ZerionisContext.clear()


class TestFormatterZerionisEvent:
    def test_direct_event_serialization(self) -> None:
        event = ZerionisLogEvent(
            timestamp="2024-01-15T10:30:00Z",
            level="INFO",
            logger="test",
            message="Request completed",
            event_type=EventType.REQUEST_END,
            service=ServiceInfo(name="api", environment="prod", version="2.0"),
            http=HttpInfo(method="GET", path="/api/test", status_code=200, duration_ms=50.0),
            duration_ms=50.0,
        )
        record = _make_record()
        record._zerionis_event = event  # type: ignore[attr-defined]
        data = _format(record)
        assert data["event_type"] == "REQUEST_END"
        assert data["http"]["method"] == "GET"
        assert data["http"]["status_code"] == 200
        assert data["duration_ms"] == 50.0

    def test_event_omits_empty_nested(self) -> None:
        event = ZerionisLogEvent(
            timestamp="2024-01-15T10:30:00Z",
            level="INFO",
            message="test",
        )
        record = _make_record()
        record._zerionis_event = event  # type: ignore[attr-defined]
        data = _format(record)
        assert "http" not in data
        assert "error" not in data
        assert "sql" not in data


class TestFormatterPrettyPrint:
    def test_pretty_output(self) -> None:
        cfg = ZerionisConfig(service_name="pp", environment="dev", version="0.0.1", pretty_print=True)
        fmt = ZerionisFormatter(cfg)
        raw = fmt.format(_make_record())
        # Pretty JSON contains newlines
        assert "\n" in raw


class TestFormatterExcInfo:
    def test_exception_info(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = _make_record(level=logging.ERROR)
            record.exc_info = sys.exc_info()
            data = _format(record)
            assert data["error"]["type"] == "ValueError"
            assert data["error"]["message"] == "boom"
            assert "Traceback" in data["error"]["stacktrace"]
