"""Core data models for structured log events."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventType(str, Enum):
    REQUEST_START = "REQUEST_START"
    REQUEST_END = "REQUEST_END"
    REQUEST_ERROR = "REQUEST_ERROR"
    METHOD_SLOW = "METHOD_SLOW"
    METHOD_ERROR = "METHOD_ERROR"
    APPLICATION_ERROR = "APPLICATION_ERROR"
    SQL_SLOW = "SQL_SLOW"
    SQL_ERROR = "SQL_ERROR"
    APPLICATION_LOG = "APPLICATION_LOG"


class ServiceInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    environment: str
    version: str


class HttpInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    duration_ms: float | None = None


class ErrorInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str | None = None
    message: str | None = None
    stacktrace: str | None = None


class SqlInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str | None = None
    duration_ms: float | None = None


class ZerionisLogEvent(BaseModel):
    """Canonical structured log event.

    When serialized, any field that is ``None`` or empty is omitted.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = "1.0"
    timestamp: str
    level: str
    logger: str | None = None
    message: str
    event_type: EventType | None = None

    service: ServiceInfo | None = None
    trace_id: str | None = None
    request_id: str | None = None

    http: HttpInfo | None = None
    user_id: str | None = None
    error: ErrorInfo | None = None
    sql: SqlInfo | None = None
    extra: dict[str, Any] | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict, omitting ``None`` and empty values."""
        data = self.model_dump(mode="python")
        return _strip_empty(data)


def _strip_empty(obj: Any) -> Any:
    """Recursively remove keys whose values are None, empty dict, or empty string."""
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            v = _strip_empty(v)
            if v is None:
                continue
            if isinstance(v, dict) and not v:
                continue
            if isinstance(v, str) and not v:
                continue
            cleaned[k] = v
        return cleaned
    if isinstance(obj, list):
        return [_strip_empty(i) for i in obj]
    return obj
