"""Zerionis Log -- Structured JSON logging for Python/FastAPI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from zerionis_log.config import ZerionisConfig
from zerionis_log.context import ZerionisContext
from zerionis_log.decorators import log_slow
from zerionis_log.formatter import ZerionisFormatter

if TYPE_CHECKING:
    from zerionis_log.middleware.fastapi import ZerionisMiddleware

__all__ = [
    "setup_logging",
    "ZerionisConfig",
    "ZerionisContext",
    "ZerionisMiddleware",
    "log_slow",
]


def setup_logging(
    config: ZerionisConfig | None = None,
    replace_handlers: bool = False,
) -> ZerionisConfig:
    """One-call setup: configures Python logging with the Zerionis JSON formatter.

    Args:
        config: Optional configuration instance.
        replace_handlers: If True, remove all existing root logger handlers
            before adding the Zerionis handler. Default is False.

    Returns the resolved configuration instance.
    """
    cfg = config or ZerionisConfig()

    # Share config with decorators module
    from zerionis_log import decorators as _dec

    _dec._config = cfg

    # Propagate max_extra_fields to context
    ZerionisContext.configure(cfg.max_extra_fields)

    formatter = ZerionisFormatter(cfg)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.name = "zerionis"

    root = logging.getLogger()

    if replace_handlers:
        root.handlers.clear()
        root.addHandler(handler)
    else:
        # Avoid duplicates: only add if no Zerionis handler exists
        has_zerionis = any(getattr(h, "name", None) == "zerionis" for h in root.handlers)
        if not has_zerionis:
            root.addHandler(handler)

    root.setLevel(logging.DEBUG)

    return cfg


def __getattr__(name: str):  # noqa: ANN001
    # Lazy import to avoid hard dependency on starlette
    if name == "ZerionisMiddleware":
        from zerionis_log.middleware.fastapi import ZerionisMiddleware

        return ZerionisMiddleware
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
