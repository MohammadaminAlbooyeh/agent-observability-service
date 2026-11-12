"""Simple in-memory rate limiting middleware."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket style rate limiter keyed by client IP."""

    def __init__(self, app, calls: int = 60, period: float = 60.0):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._tokens: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        key = self._client_key(request)
        now = time.time()
        window = self._tokens[key]
        # Remove timestamps outside the window
        self._tokens[key] = [t for t in window if now - t < self.period]
        if len(self._tokens[key]) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"X-Request-ID": getattr(request.state, "request_id", "")},
            )
        self._tokens[key].append(now)
        return await call_next(request)
