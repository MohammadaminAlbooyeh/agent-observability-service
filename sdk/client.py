"""HTTP client that batches and POSTs spans to this service."""

import time
import uuid
from typing import Any

import httpx


class ObservabilityClient:
    """Client that batches spans locally and POSTs them to the observability service."""

    def __init__(self, base_url: str, api_key: str, batch_size: int = 10):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.batch_size = batch_size
        self._batch: list[dict[str, Any]] = []
        self._client = httpx.AsyncClient(timeout=10.0)

    def send_span(
        self,
        name: str,
        duration_ms: float,
        metadata: dict | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        """Add a span to the local batch and flush if batch_size is reached."""
        self._batch.append(
            {
                "trace_id": trace_id or str(uuid.uuid4()),
                "span_id": span_id or str(uuid.uuid4()),
                "parent_id": parent_id,
                "name": name,
                "start_time": time.time(),
                "end_time": time.time() + (duration_ms / 1000.0),
                "duration_ms": duration_ms,
                "metadata": metadata or {},
            }
        )
        if len(self._batch) >= self.batch_size:
            self.flush_sync()

    def flush_sync(self) -> None:
        """Synchronously POST the batched spans (best-effort)."""
        if not self._batch:
            return
        spans = list(self._batch)
        self._batch = []
        try:
            import asyncio

            asyncio.run(self._post_batch(spans))
        except Exception:  # noqa: BLE001
            # Best-effort; never raise from the SDK.
            pass

    async def flush(self) -> None:
        """Asynchronously POST the batched spans."""
        if not self._batch:
            return
        spans = list(self._batch)
        self._batch = []
        await self._post_batch(spans)

    async def _post_batch(self, spans: list[dict[str, Any]]) -> None:
        """POST a batch of spans to the /traces/batch endpoint."""
        try:
            await self._client.post(
                f"{self.base_url}/traces/batch",
                json={"spans": spans},
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            )
        except Exception:  # noqa: BLE001
            pass

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def __enter__(self) -> "ObservabilityClient":
        return self

    def __exit__(self, *args) -> None:
        try:
            self.flush_sync()
        finally:
            try:
                import asyncio

                asyncio.run(self._client.aclose())
            except Exception:  # noqa: BLE001
                pass
