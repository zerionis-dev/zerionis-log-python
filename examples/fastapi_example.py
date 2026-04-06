"""Minimal FastAPI application demonstrating zerionis-log setup.

Run with::

    uvicorn examples.fastapi_example:app --reload
"""

from __future__ import annotations

import asyncio

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from zerionis_log import ZerionisConfig, ZerionisMiddleware, log_slow, setup_logging
from zerionis_log.context import ZerionisContext

# 1. Configure and install the formatter
config = setup_logging(
    ZerionisConfig(
        service_name="demo-api",
        environment="development",
        version="0.1.0",
        pretty_print=True,
        request_start_enabled=True,
    )
)


# 2. Define endpoints
@log_slow(threshold_ms=100)
async def slow_task(n: int) -> int:
    await asyncio.sleep(n / 1000)
    return n


async def homepage(request: Request) -> JSONResponse:
    ZerionisContext.put("action", "homepage")
    result = await slow_task(150)
    return JSONResponse({"message": "Hello, structured logging!", "computed": result})


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# 3. Build app and add middleware
app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/health", health),
    ],
)
app.add_middleware(ZerionisMiddleware, config=config)
