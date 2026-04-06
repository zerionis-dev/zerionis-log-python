# zerionis-log

Structured JSON logging for Python and FastAPI. Converts standard Python logs into rich, structured JSON with minimal setup.

## Features

- **Structured JSON output** with a frozen schema contract
- **FastAPI/Starlette middleware** for automatic request/response logging
- **Async-safe context** via `ContextVar` (trace IDs, request IDs, custom fields)
- **Deep field sanitization** with partial redaction for sensitive data
- **`@log_slow` decorator** for sync and async functions
- **Optional integrations**: OpenTelemetry, SQLAlchemy, orjson
- **Zero hard dependencies** beyond Pydantic v2

## Quick Start

```bash
pip install zerionis-log
```

```python
from zerionis_log import setup_logging, ZerionisConfig, ZerionisMiddleware

# 1. Setup
config = setup_logging(ZerionisConfig(
    service_name="my-api",
    environment="production",
    version="1.0.0",
))

# 2. Add middleware (FastAPI / Starlette)
app.add_middleware(ZerionisMiddleware, config=config)
```

Every log line is now structured JSON:

```json
{
  "schema_version": "1.0",
  "timestamp": "2024-01-15T10:30:00.123456+00:00",
  "level": "INFO",
  "message": "GET /api/users 200",
  "event_type": "REQUEST_END",
  "service": {"name": "my-api", "environment": "production", "version": "1.0.0"},
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "http": {"method": "GET", "path": "/api/users", "status_code": 200, "duration_ms": 45.12},
  "duration_ms": 45.12
}
```

## Configuration

All settings are configurable via environment variables with the `ZERIONIS_LOG_` prefix:

```bash
export ZERIONIS_LOG_SERVICE_NAME=payments-api
export ZERIONIS_LOG_ENVIRONMENT=production
export ZERIONIS_LOG_SLOW_METHOD_THRESHOLD_MS=500
```

Or in code:

```python
config = ZerionisConfig(
    service_name="payments-api",
    sanitize_fields=["x-custom-secret"],
    exclude_endpoints=["/health", "/ready"],
    pretty_print=True,
)
```

## Decorators

```python
from zerionis_log import log_slow

@log_slow(threshold_ms=500, exclude_args=["password"])
async def process_payment(amount: float, password: str):
    ...
```

## Context

```python
from zerionis_log import ZerionisContext

ZerionisContext.put("tenant_id", "acme-corp")
```

## Optional Extras

```bash
pip install zerionis-log[fastapi]   # Starlette middleware
pip install zerionis-log[sql]       # SQLAlchemy query logging
pip install zerionis-log[otel]      # OpenTelemetry trace extraction
pip install zerionis-log[fast]      # orjson for faster serialization
```

## License

Apache 2.0
