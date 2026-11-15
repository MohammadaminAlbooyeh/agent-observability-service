"""HTTP client that buffers spans and POSTs them to the observability service."""

import atexit
import logging
import threading
import time
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger("agent_observability")

RETRY_STATUSES = {409, 429, 500, 502, 503, 504}


class ObservabilityClient:
    """Buffers spans and sends them to ``POST {base_url}/ingestion/batch``.

    Thread-safe. Spans are flushed when ``batch_size`` is reached, on ``flush()``,
    on ``close()`` / context-manager exit, and at interpreter exit. Delivery is
    best-effort: failures are retried, then logged, and never raised into agent code.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        batch_size: int = 50,
        timeout: float = 10.0,
        max_retries: int = 3,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._http = httpx.Client(
            timeout=timeout,
            headers={"X-API-Key": api_key, "User-Agent": "agent-observability-sdk"},
            transport=transport,
        )
        self._closed = False
        atexit.register(self.close)

    def send_span(
        self,
        *,
        trace_id: str,
        span_id: str,
        name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        parent_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Queue a span. ``start_time``/``end_time`` should be timezone-aware."""
        span = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_id": parent_id,
            "name": name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }
        with self._lock:
            self._buffer.append(span)
            should_flush = len(self._buffer) >= self.batch_size
        if should_flush:
            self.flush()

    def flush(self) -> bool:
        """Send all buffered spans. Returns True if everything was delivered."""
        with self._lock:
            spans, self._buffer = self._buffer, []
        ok = True
        for i in range(0, len(spans), 1000):
            ok = self._post(spans[i : i + 1000]) and ok
        return ok

    def _post(self, spans: list[dict[str, Any]]) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.post(f"{self.base_url}/ingestion/batch", json=spans)
                if resp.status_code < 300:
                    return True
                if resp.status_code not in RETRY_STATUSES:
                    logger.warning(
                        "Dropping %d spans: HTTP %d %s", len(spans), resp.status_code, resp.text
                    )
                    return False
                error = f"HTTP {resp.status_code}"
            except httpx.HTTPError as exc:
                error = str(exc)
            if attempt < self.max_retries:
                time.sleep(min(0.5 * 2**attempt, 5.0))
        logger.warning("Dropping %d spans after %d retries: %s", len(spans), self.max_retries, error)
        return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.flush()
        finally:
            self._http.close()
            atexit.unregister(self.close)

    def __enter__(self) -> "ObservabilityClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
