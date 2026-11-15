"""Rate limiting, request IDs, and the generic error handler."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.middleware.error_handler import register_exception_handlers
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_id import RequestIDMiddleware


def make_app(calls: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, calls=calls, period=60)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internal detail")

    return app


async def test_rate_limit_with_retry_after_and_request_id():
    app = make_app(calls=2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        assert (await client.get("/ok")).status_code == 200
        assert (await client.get("/ok")).status_code == 200
        limited = await client.get("/ok")
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) >= 1
        assert limited.headers["X-Request-ID"]
        assert (await client.get("/health")).status_code == 200


async def test_request_id_propagated():
    app = make_app(calls=10)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/ok", headers={"X-Request-ID": "abc"})
        assert resp.headers["X-Request-ID"] == "abc"


async def test_error_handler_hides_internals():
    app = make_app(calls=10)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/boom", headers={"X-Request-ID": "rid-1"})
        assert resp.status_code == 500
        assert resp.json() == {"detail": "Internal server error", "request_id": "rid-1"}
        assert "secret" not in resp.text
