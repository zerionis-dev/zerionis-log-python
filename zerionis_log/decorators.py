"""Decorators for method-level structured logging."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
import traceback as tb_mod
from datetime import datetime, timezone
from typing import Any, Callable

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.models import (
    ErrorInfo,
    EventType,
    ServiceInfo,
    ZerionisLogEvent,
)
from zerionis_log.validator import sanitize_message

_logger = logging.getLogger("zerionis_log.decorators")

# Module-level config; set by setup_logging
_config: ZerionisConfig | None = None


def _get_config() -> ZerionisConfig:
    global _config
    if _config is None:
        _config = ZerionisConfig()
    return _config


def log_slow(
    threshold_ms: float | None = None,
    exclude_args: list[str] | None = None,
) -> Callable[..., Any]:
    """Decorator that emits ``METHOD_SLOW`` / ``METHOD_ERROR`` events.

    Works with both sync and async functions.

    Args:
        threshold_ms: Override the global slow-method threshold.
        exclude_args: Parameter names to exclude from logged arguments.
    """
    _exclude = set(exclude_args or [])

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)

        def _build_args_dict(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            return {
                k: repr(v)
                for k, v in bound.arguments.items()
                if k not in _exclude and k != "self"
            }

        def _emit(
            event_type: EventType,
            duration_ms: float,
            args_dict: dict[str, Any],
            error: ErrorInfo | None = None,
        ) -> None:
            cfg = _get_config()
            ctx = ZerionisContext.get()
            service = ServiceInfo(
                name=cfg.service_name,
                environment=cfg.environment,
                version=cfg.version,
            )
            event = ZerionisLogEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level="WARN" if event_type == EventType.METHOD_SLOW else "ERROR",
                logger=f"{fn.__module__}.{fn.__qualname__}",
                message=f"{fn.__qualname__} took {duration_ms:.2f}ms",
                event_type=event_type,
                service=service,
                trace_id=ctx.get("trace_id"),
                request_id=ctx.get("request_id"),
                user_id=ctx.get("user_id"),
                error=error,
                extra={"args": args_dict} if args_dict else None,
                duration_ms=round(duration_ms, 2),
            )
            record = logging.LogRecord(
                name="zerionis_log.decorators",
                level=logging.WARNING if event_type == EventType.METHOD_SLOW else logging.ERROR,
                pathname="",
                lineno=0,
                msg="",
                args=(),
                exc_info=None,
            )
            record._zerionis_event = event  # type: ignore[attr-defined]
            _logger.handle(record)

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cfg = _get_config()
                thresh = threshold_ms if threshold_ms is not None else cfg.slow_method_threshold_ms
                start = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    if elapsed >= thresh:
                        _emit(EventType.METHOD_SLOW, elapsed, _build_args_dict(args, kwargs))
                    return result
                except Exception as exc:
                    elapsed = (time.perf_counter() - start) * 1000
                    stacktrace = "".join(
                        tb_mod.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    _emit(
                        EventType.METHOD_ERROR,
                        elapsed,
                        _build_args_dict(args, kwargs),
                        error=ErrorInfo(
                            type=type(exc).__name__,
                            message=sanitize_message(str(exc)),
                            stacktrace=stacktrace,
                        ),
                    )
                    raise

            return async_wrapper
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cfg = _get_config()
                thresh = threshold_ms if threshold_ms is not None else cfg.slow_method_threshold_ms
                start = time.perf_counter()
                try:
                    result = fn(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    if elapsed >= thresh:
                        _emit(EventType.METHOD_SLOW, elapsed, _build_args_dict(args, kwargs))
                    return result
                except Exception as exc:
                    elapsed = (time.perf_counter() - start) * 1000
                    stacktrace = "".join(
                        tb_mod.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    _emit(
                        EventType.METHOD_ERROR,
                        elapsed,
                        _build_args_dict(args, kwargs),
                        error=ErrorInfo(
                            type=type(exc).__name__,
                            message=sanitize_message(str(exc)),
                            stacktrace=stacktrace,
                        ),
                    )
                    raise

            return sync_wrapper

    return decorator
