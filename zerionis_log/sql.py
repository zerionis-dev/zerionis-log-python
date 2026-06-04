"""Optional SQLAlchemy query logging via event listeners."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.models import (
    EventType,
    ServiceInfo,
    SqlInfo,
    ZerionisLogEvent,
)

_logger = logging.getLogger("zerionis_log.sql")
_MAX_SQL_LEN = 4096


def install_sql_hooks(engine: Any, config: ZerionisConfig | None = None) -> None:
    """Attach ``before_cursor_execute`` / ``after_cursor_execute`` listeners.

    Requires ``sqlalchemy`` to be installed.
    """
    from sqlalchemy import event  # type: ignore[import-untyped]

    cfg = config or ZerionisConfig()
    service = ServiceInfo(
        name=cfg.service_name,
        environment=cfg.environment,
        version=cfg.version,
    )

    def before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        context._zerionis_start = time.perf_counter()

    def after_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        start = getattr(context, "_zerionis_start", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000
        query = statement[:_MAX_SQL_LEN]

        if duration_ms >= cfg.slow_sql_threshold_ms:
            _emit(service, cfg, EventType.SQL_SLOW, query, duration_ms)

    def handle_error(exception_context: Any) -> None:
        cursor_context = getattr(exception_context, "execution_context", None)
        start = getattr(cursor_context, "_zerionis_start", None) if cursor_context else None
        duration_ms = (time.perf_counter() - start) * 1000 if start else 0
        statement = getattr(exception_context, "statement", "") or ""
        query = statement[:_MAX_SQL_LEN]
        _emit(service, cfg, EventType.SQL_ERROR, query, duration_ms)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    event.listen(engine, "handle_error", handle_error)


def _emit(
    service: ServiceInfo,
    config: ZerionisConfig,
    event_type: EventType,
    query: str,
    duration_ms: float,
) -> None:
    ctx = ZerionisContext.get()
    event = ZerionisLogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        level="WARNING" if event_type == EventType.SQL_SLOW else "ERROR",
        logger="zerionis_log.sql",
        message=f"SQL {event_type.value}: {query[:120]}",
        event_type=event_type,
        service=service,
        trace_id=ctx.get("trace_id"),
        request_id=ctx.get("request_id"),
        sql=SqlInfo(query=query, duration_ms=round(duration_ms, 2)),
        duration_ms=round(duration_ms, 2),
    )
    record = logging.LogRecord(
        name="zerionis_log.sql",
        level=logging.WARNING if event_type == EventType.SQL_SLOW else logging.ERROR,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )
    record._zerionis_event = event  # type: ignore[attr-defined]
    _logger.handle(record)
