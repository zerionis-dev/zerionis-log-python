"""Tests for the FastAPI/Starlette ASGI middleware."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from zerionis_log.config import ZerionisConfig
from zerionis_log.middleware.fastapi import ZerionisMiddleware


async def homepage(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def error_endpoint(request: Request) -> JSONResponse:
    raise ValueError("test error")


async def server_error(request: Request) -> PlainTextResponse:
    return PlainTextResponse("error", status_code=500)


async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_app(config: ZerionisConfig | None = None) -> Starlette:
    cfg = config or ZerionisConfig(service_name="test", environment="test", version="0.1.0")
    app = Starlette(
        routes=[
            Route("/", homepage),
            Route("/error", error_endpoint),
            Route("/server-error", server_error),
            Route("/health", health),
        ],
    )
    app.add_middleware(ZerionisMiddleware, config=cfg)
    return app


@pytest.fixture
def app() -> Starlette:
    return _make_app()


@pytest.fixture
async def client(app: Starlette) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestMiddlewareLifecycle:
    async def test_success_response(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "x-trace-id" in resp.headers
        assert "x-request-id" in resp.headers

    async def test_trace_id_from_header(self, client: AsyncClient) -> None:
        trace = "550e8400-e29b-41d4-a716-446655440000"
        resp = await client.get("/", headers={"X-Trace-Id": trace})
        assert resp.headers["x-trace-id"] == trace

    async def test_invalid_trace_id_generates_new(self, client: AsyncClient) -> None:
        resp = await client.get("/", headers={"X-Trace-Id": "invalid"})
        # Should get a valid UUID back
        assert len(resp.headers["x-trace-id"]) == 36

    async def test_request_id_format(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        rid = resp.headers["x-request-id"]
        assert rid.startswith("req-")
        # Full uuid4 hex = 32 chars + "req-" prefix = 36 chars
        assert len(rid) == 36


class TestMiddlewareExcluded:
    async def test_excluded_endpoint_no_headers(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        # Excluded endpoints don't add trace headers
        assert "x-trace-id" not in resp.headers


class TestMiddlewareErrors:
    async def test_exception_returns_500(self, client: AsyncClient) -> None:
        with pytest.raises(Exception):
            await client.get("/error")

    async def test_5xx_status(self, client: AsyncClient) -> None:
        resp = await client.get("/server-error")
        assert resp.status_code == 500
        assert "x-trace-id" in resp.headers


class TestMiddlewareRequestStart:
    async def test_request_start_enabled(self) -> None:
        cfg = ZerionisConfig(
            service_name="test",
            environment="test",
            version="0.1.0",
            request_start_enabled=True,
        )
        app = _make_app(cfg)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/")
            assert resp.status_code == 200
