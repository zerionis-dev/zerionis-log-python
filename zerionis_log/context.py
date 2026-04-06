"""Async-safe context management via ContextVar."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from zerionis_log.validator import validate_extra_key

_logger = logging.getLogger("zerionis_log")

_ctx: ContextVar[dict[str, Any] | None] = ContextVar("zerionis_log_ctx", default=None)

_MAX_KEY_LEN = 128
_MAX_VALUE_LEN = 4096


class ZerionisContext:
    """Thread-safe, async-safe request context backed by ``ContextVar``."""

    _max_extra: int = 20
    _overflow_warned: bool = False

    @classmethod
    def configure(cls, max_extra: int) -> None:
        """Set the maximum number of extra fields allowed."""
        cls._max_extra = max_extra
        cls._overflow_warned = False

    @staticmethod
    def set(
        *,
        trace_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize context for the current task/request."""
        data: dict[str, Any] = {}
        if trace_id is not None:
            data["trace_id"] = trace_id
        if request_id is not None:
            data["request_id"] = request_id
        if user_id is not None:
            data["user_id"] = user_id
        data["_extra"] = {}
        for k, v in kwargs.items():
            data["_extra"][validate_extra_key(k)] = _truncate(v)
        _ctx.set(data)

    @staticmethod
    def get() -> dict[str, Any]:
        """Return a snapshot of the current context."""
        raw = _ctx.get()
        if raw is None:
            return {}
        result = {k: v for k, v in raw.items() if k != "_extra"}
        extra = raw.get("_extra", {})
        if extra:
            result["extra"] = dict(extra)
        return result

    @classmethod
    def put(cls, key: str, value: Any) -> None:
        """Add a custom extra field to the current context."""
        raw = _ctx.get()
        if raw is None:
            _logger.warning("ZerionisContext.put() called before context was initialized")
            return
        extra: dict[str, Any] = raw.setdefault("_extra", {})
        if len(extra) >= cls._max_extra and key not in extra:
            if not cls._overflow_warned:
                _logger.warning(
                    "Max extra fields (%d) reached, dropping key %r",
                    cls._max_extra,
                    key,
                )
                cls._overflow_warned = True
            return
        extra[validate_extra_key(key)] = _truncate(value)

    @staticmethod
    def clear() -> None:
        """Clear the current context (call in ``finally`` blocks)."""
        _ctx.set(None)


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_VALUE_LEN:
        return value[:_MAX_VALUE_LEN]
    return value
