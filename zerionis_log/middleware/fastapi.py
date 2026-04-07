"""ASGI middleware for FastAPI / Starlette."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.models import (
    ErrorInfo,
    EventType,
    HttpInfo,
    ServiceInfo,
    ZerionisLogEvent,
)
from zerionis_log.otel import generate_trace_id, get_otel_trace_id
from zerionis_log.sanitizer import Sanitizer
from zerionis_log.validator import is_valid_trace_id, sanitize_message, sanitize_path

_logger = logging.getLogger("zerionis_log.middleware")


class ZerionisMiddleware:
    """Pure ASGI middleware that emits structured request events.

    Avoids ``BaseHTTPMiddleware`` to prevent streaming/cancellation issues.
    """

    def __init__(self, app: Any, config: ZerionisConfig | None = None) -> None:
        self.app = app
        self._config = config or ZerionisConfig()
        self._service = ServiceInfo(
            name=self._config.service_name,
            environment=self._config.environment,
            version=self._config.version,
        )
        self._sanitizer = Sanitizer(
            extra_fields=self._config.sanitize_fields,
            partial_redaction=self._config.partial_redaction,
            enabled=self._config.sanitize_enabled,
        )

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = sanitize_path(scope.get("path", "/"))

        # Skip excluded endpoints
        if any(path.startswith(ep) for ep in self._config.exclude_endpoints):
            await self.app(scope, receive, send)
            return

        # Extract headers
        headers_raw: list[tuple[bytes, bytes]] = scope.get("headers", [])
        headers_dict: dict[str, str] = {}
        for k, v in headers_raw:
            headers_dict[k.decode("latin-1").lower()] = v.decode("latin-1")

        # Resolve trace_id
        trace_id = headers_dict.get("x-trace-id")
        if not trace_id or not is_valid_trace_id(trace_id):
            trace_id = get_otel_trace_id() or generate_trace_id()

        request_id = f"req-{uuid.uuid4().hex}"

        ZerionisContext.set(trace_id=trace_id, request_id=request_id)

        method = scope.get("method", "")
        client = scope.get("client")
        client_ip = client[0] if client else None
        ua_raw = headers_dict.get("user-agent")
        user_agent = ua_raw[:512] if ua_raw else None

        if self._config.request_start_enabled:
            self._emit_event(
                EventType.REQUEST_START,
                message=f"{method} {path}",
                http=HttpInfo(
                    method=method,
                    path=path,
                    client_ip=client_ip,
                    user_agent=user_agent,
                ),
                trace_id=trace_id,
                request_id=request_id,
            )

        status_code: int | None = None
        response_started = False

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                response_started = True
                # Inject trace headers
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode()))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = (time.perf_counter() - start) * 1000

            sc = status_code or 200
            event_type = EventType.REQUEST_END if sc < 500 else EventType.REQUEST_ERROR

            self._emit_event(
                event_type,
                message=f"{method} {path} {sc}",
                http=HttpInfo(
                    method=method,
                    path=path,
                    status_code=sc,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    duration_ms=round(duration_ms, 2),
                ),
                trace_id=trace_id,
                request_id=request_id,
                duration_ms=round(duration_ms, 2),
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            import traceback as tb_mod

            stacktrace = "".join(tb_mod.format_exception(type(exc), exc, exc.__traceback__))
            lines = stacktrace.splitlines()
            if len(lines) > self._config.max_stacktrace_lines:
                stacktrace = "\n".join(lines[: self._config.max_stacktrace_lines])

            exc_msg = sanitize_message(str(exc))
            self._emit_event(
                EventType.REQUEST_ERROR,
                message=f"{method} {path} 500 - {type(exc).__name__}: {exc_msg}",
                http=HttpInfo(
                    method=method,
                    path=path,
                    status_code=500,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    duration_ms=round(duration_ms, 2),
                ),
                error=ErrorInfo(
                    type=type(exc).__name__,
                    message=exc_msg,
                    stacktrace=stacktrace,
                ),
                trace_id=trace_id,
                request_id=request_id,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            ZerionisContext.clear()

    def _emit_event(
        self,
        event_type: EventType,
        *,
        message: str,
        http: HttpInfo | None = None,
        error: ErrorInfo | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        event = ZerionisLogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="ERROR" if error else "INFO",
            logger="zerionis_log.middleware",
            message=message,
            event_type=event_type,
            service=self._service,
            trace_id=trace_id,
            request_id=request_id,
            http=http,
            error=error,
            duration_ms=duration_ms,
        )
        record = logging.LogRecord(
            name="zerionis_log.middleware",
            level=logging.ERROR if error else logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        record._zerionis_event = event  # type: ignore[attr-defined]
        _logger.handle(record)
