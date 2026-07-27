"""Input validation for structured log fields."""

from __future__ import annotations

import ipaddress
import re

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_OTEL_TRACE_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

_REQUEST_ID_RE = re.compile(r"^req-[a-zA-Z0-9]+$")

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_MAX_PATH_LEN = 2048
_MAX_MESSAGE_LEN = 10_000
_MAX_EXTRA_KEY_LEN = 128
_MAX_EXTRA_VALUE_LEN = 4096


def is_valid_trace_id(value: str) -> bool:
    """Check if *value* matches UUID v4 format or 32-hex OTel trace ID."""
    return bool(_UUID4_RE.match(value) or _OTEL_TRACE_RE.match(value))


def is_valid_request_id(value: str) -> bool:
    """Check ``req-`` prefix followed by alphanumeric chars."""
    return bool(_REQUEST_ID_RE.match(value))


def sanitize_path(path: str) -> str:
    """Strip control characters and truncate to max length."""
    path = _CONTROL_CHARS.sub("", path)
    return path[:_MAX_PATH_LEN]


def sanitize_message(message: str) -> str:
    """Strip control characters and truncate to max length."""
    message = _CONTROL_CHARS.sub("", message)
    return message[:_MAX_MESSAGE_LEN]


def is_valid_ip(value: str) -> bool:
    """Return True if *value* is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_extra_key(key: str) -> str:
    """Truncate and clean an extra-field key."""
    return _CONTROL_CHARS.sub("", key)[:_MAX_EXTRA_KEY_LEN]


