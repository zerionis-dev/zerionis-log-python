"""Optional OpenTelemetry integration.

Extracts ``trace_id`` and ``span_id`` from the current OTel span when
the ``opentelemetry-api`` package is installed. Falls back to UUID v4.
"""

from __future__ import annotations

import uuid


def get_otel_trace_id() -> str | None:
    """Return the current OTel trace ID as a hex string, or ``None``."""
    try:
        from opentelemetry import trace  # type: ignore[import-untyped]

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None


def generate_trace_id() -> str:
    """Generate a UUID v4 trace ID."""
    return str(uuid.uuid4())
