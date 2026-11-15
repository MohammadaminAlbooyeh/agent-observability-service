"""Sliding-window rate limiter keyed by client IP.

State is in-process memory: with N workers/replicas the effective limit is N x calls.
Use a shared store (e.g. Redis) or the reverse proxy for a global limit.
"""

import time
from collections import deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

EXEMPT_PATHS = {"/health"}
MAX_TRACKED_CLIENTS = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: float = 60.0):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, now: float) -> None:
        stale = [k for k, q in self._hits.items() if not q or now - q[-1] >= self.period]
        for key in stale:
            del self._hits[key]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._prune(now)

        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.period:
            hits.popleft()
        if len(hits) >= self.calls:
            retry_after = max(int(self.period - (now - hits[0])) + 1, 1)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return await call_next(request)
