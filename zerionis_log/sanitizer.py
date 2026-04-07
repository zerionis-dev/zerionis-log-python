"""Deep field redaction for sensitive data."""

from __future__ import annotations

import re
from typing import Any

_DEFAULT_SENSITIVE: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pass",
        "pwd",
        "token",
        "secret",
        "api_key",
        "apikey",
        "api-key",
        "card_number",
        "cvv",
        "authorization",
        "access_token",
        "refresh_token",
        "cookie",
        "set_cookie",
        "set-cookie",
        "ssn",
        "credit_score",
        "bearer",
        "jwt",
        "private_key",
        "privatekey",
        "signing_key",
        "session",
        "session_id",
        "sessionid",
        "client_secret",
        "clientsecret",
        "credentials",
        "otp",
        "mfa_code",
    }
)

_SENSITIVE_PATTERNS: tuple[str, ...] = ("secret", "token", "password", "credential", "auth")

_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    }
)

REDACTED = "[REDACTED]"
_PARTIAL_THRESHOLD = 20
_MAX_DEPTH = 32


def _normalize_key(key: str) -> str:
    return key.lower().replace("-", "_").replace(" ", "_")


class Sanitizer:
    """Recursively redacts sensitive fields from nested structures."""

    def __init__(
        self,
        *,
        extra_fields: list[str] | None = None,
        partial_redaction: bool = True,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._partial = partial_redaction
        fields = set(_DEFAULT_SENSITIVE)
        if extra_fields:
            fields.update(f.lower() for f in extra_fields)
        self._sensitive = frozenset(fields)
        # Pre-build normalized lookup for faster matching
        self._sensitive_normalized = frozenset(_normalize_key(f) for f in self._sensitive)

    def sanitize(self, data: Any) -> Any:
        """Return a sanitized copy of *data*."""
        if not self._enabled:
            return data
        return self._walk(data, 0, set())

    def sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize HTTP headers."""
        if not self._enabled:
            return headers
        result: dict[str, str] = {}
        for k, v in headers.items():
            if k.lower() in _SENSITIVE_HEADERS or _normalize_key(k) in self._sensitive_normalized:
                result[k] = self._redact(v)
            else:
                result[k] = v
        return result

    # ------------------------------------------------------------------

    def _walk(self, obj: Any, depth: int, seen: set[int]) -> Any:
        if depth > _MAX_DEPTH:
            return "[MAX_DEPTH]"
        obj_id = id(obj)
        if isinstance(obj, (dict, list, tuple)) and obj_id in seen:
            return "[CIRCULAR]"
        if isinstance(obj, dict):
            seen.add(obj_id)
            result = {k: self._process_kv(k, v, depth, seen) for k, v in obj.items()}
            seen.discard(obj_id)
            return result
        if isinstance(obj, (list, tuple)):
            seen.add(obj_id)
            result_list = [self._walk(item, depth + 1, seen) for item in obj]
            seen.discard(obj_id)
            return result_list
        return obj

    def _is_sensitive(self, key: str) -> bool:
        normalized = _normalize_key(key)
        if normalized in self._sensitive_normalized:
            return True
        return any(p in normalized for p in _SENSITIVE_PATTERNS)

    def _process_kv(self, key: str, value: Any, depth: int, seen: set[int]) -> Any:
        if self._is_sensitive(key):
            if isinstance(value, str):
                return self._redact(value)
            return REDACTED
        return self._walk(value, depth + 1, seen)

    def _redact(self, value: str) -> str:
        if not self._partial or len(value) < _PARTIAL_THRESHOLD:
            return REDACTED
        return f"{value[:4]}...{value[-4:]}"
