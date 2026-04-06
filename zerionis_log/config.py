"""Configuration for Zerionis structured logging."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ZerionisConfig(BaseSettings):
    """Structured logging configuration.

    All fields can be overridden via environment variables with the
    ``ZERIONIS_LOG_`` prefix. For example, ``ZERIONIS_LOG_SERVICE_NAME=payments``.
    """

    model_config = SettingsConfigDict(env_prefix="ZERIONIS_LOG_")

    # Service identity
    service_name: str = "unknown"
    environment: str = "development"
    version: str = "0.0.0"

    # Thresholds
    slow_method_threshold_ms: float = 1000.0
    slow_sql_threshold_ms: float = 500.0
    max_stacktrace_lines: int = 25
    max_extra_fields: int = 20

    # Request body capture
    request_start_enabled: bool = False
    include_request_body: bool = False
    include_response_body: bool = False
    body_content_types: list[str] = Field(default_factory=lambda: ["application/json"])
    max_body_size: int = 8192

    # Sanitization
    sanitize_enabled: bool = True
    sanitize_fields: list[str] = Field(default_factory=list)
    partial_redaction: bool = True

    # Endpoint filtering
    exclude_endpoints: list[str] = Field(
        default_factory=lambda: ["/health", "/ready", "/metrics"]
    )

    # Optional integrations
    sql_enabled: bool = False

    # Output
    pretty_print: bool = False
