"""Custom ``logging.Formatter`` that emits structured JSON."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.models import (
    ErrorInfo,
    EventType,
    ServiceInfo,
    ZerionisLogEvent,
    _strip_empty,
)
from zerionis_log.sanitizer import Sanitizer
from zerionis_log.validator import sanitize_message

# Try fast JSON serializer, fall back to stdlib.
try:
    import orjson as _json_mod  # type: ignore[import-untyped]

    def _dumps(obj: Any, *, pretty: bool = False) -> str:
        opts = _json_mod.OPT_NON_STR_KEYS
        if pretty:
            opts |= _json_mod.OPT_INDENT_2
        return _json_mod.dumps(obj, option=opts).decode()

except ImportError:
    import json as _json_stdlib

    def _dumps(obj: Any, *, pretty: bool = False) -> str:  # type: ignore[misc]
        kw: dict[str, Any] = {"ensure_ascii": False, "default": str}
        if pretty:
            kw["indent"] = 2
        else:
            kw["separators"] = (",", ":")
        return _json_stdlib.dumps(obj, **kw)


class ZerionisFormatter(logging.Formatter):
    """Formats ``LogRecord`` instances as structured JSON.

    If the record carries a ``_zerionis_event`` attribute (set by the
    middleware or decorator), that event is serialized directly.
    Otherwise an ``APPLICATION_LOG`` event is built from the record.
    """

    def __init__(self, config: ZerionisConfig) -> None:
        super().__init__()
        self._config = config
        self._service = ServiceInfo(
            name=config.service_name,
            environment=config.environment,
            version=config.version,
        )
        self._service_dict = _strip_empty(self._service.model_dump(mode="python"))
        self._sanitizer = Sanitizer(
            extra_fields=config.sanitize_fields,
            partial_redaction=config.partial_redaction,
            enabled=config.sanitize_enabled,
        )

    def format(self, record: logging.LogRecord) -> str:
        event: ZerionisLogEvent | None = getattr(record, "_zerionis_event", None)
        if event is not None:
            data = event.to_dict()
            if "extra" in data:
                data["extra"] = self._sanitizer.sanitize(data["extra"])
            return _dumps(data, pretty=self._config.pretty_print)
        return _dumps(self._build_event(record), pretty=self._config.pretty_print)

    # ------------------------------------------------------------------

    def _build_event(self, record: logging.LogRecord) -> dict[str, Any]:
        ctx = ZerionisContext.get()

        error: dict[str, Any] | None = None
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            tb_lines = traceback.format_exception(*record.exc_info)
            stacktrace = "".join(tb_lines)
            # Truncate stacktrace
            lines = stacktrace.splitlines()
            if len(lines) > self._config.max_stacktrace_lines:
                lines = lines[: self._config.max_stacktrace_lines]
                stacktrace = "\n".join(lines)
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "stacktrace": stacktrace,
            }

        event_type = EventType.APPLICATION_LOG
        if record.levelno >= logging.ERROR:
            event_type = EventType.APPLICATION_ERROR

        msg = record.getMessage()

        data: dict[str, Any] = {
            "schema_version": "1.0",
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_message(msg),
            "event_type": event_type.value,
            "service": self._service_dict,
        }

        trace_id = ctx.get("trace_id")
        if trace_id:
            data["trace_id"] = trace_id

        request_id = ctx.get("request_id")
        if request_id:
            data["request_id"] = request_id

        user_id = ctx.get("user_id")
        if user_id:
            data["user_id"] = user_id

        if error:
            data["error"] = error

        extra = ctx.get("extra")
        if extra:
            data["extra"] = self._sanitizer.sanitize(extra)

        return data
