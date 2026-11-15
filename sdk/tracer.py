"""`with tracer.span("tool_call"): ...` context manager with automatic nesting."""

import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

_current_trace_id: ContextVar[Optional[str]] = ContextVar("obs_trace_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("obs_span_id", default=None)


class Span:
    """Handle for an in-progress span; use it to attach metadata."""

    def __init__(self, name: str, trace_id: str, parent_id: Optional[str], metadata: dict):
        self.name = name
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex
        self.parent_id = parent_id
        self.metadata: dict[str, Any] = metadata

    def set(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def set_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Record LLM usage; the service converts it to cost_usd."""
        self.metadata.update(model=model, input_tokens=input_tokens, output_tokens=output_tokens)


class Tracer:
    """Creates spans. Spans opened inside another span become its children.

    Context is tracked with contextvars, so nesting works across threads and asyncio tasks.
    """

    def __init__(self, client, version: Optional[str] = None, **default_metadata: Any):
        self.client = client
        self.default_metadata = dict(default_metadata)
        if version is not None:
            self.default_metadata["version"] = version

    @contextmanager
    def trace(self, name: str, **metadata: Any) -> Iterator[Span]:
        """Start a new trace whose root span is ``name``."""
        with self._span(name, metadata, new_trace=True) as span:
            yield span

    @contextmanager
    def span(self, name: str, **metadata: Any) -> Iterator[Span]:
        """Open a span in the current trace (or start a new trace if there is none)."""
        with self._span(name, metadata, new_trace=False) as span:
            yield span

    @contextmanager
    def _span(self, name: str, metadata: dict, new_trace: bool) -> Iterator[Span]:
        trace_id = None if new_trace else _current_trace_id.get()
        parent_id = None if trace_id is None else _current_span_id.get()
        span = Span(
            name,
            trace_id or uuid.uuid4().hex,
            parent_id,
            {**self.default_metadata, **metadata},
        )
        trace_token = _current_trace_id.set(span.trace_id)
        span_token = _current_span_id.set(span.span_id)
        start_wall = datetime.now(timezone.utc)
        start = time.perf_counter()
        try:
            yield span
        except BaseException as exc:
            span.metadata.update(
                error=True, error_type=type(exc).__name__, error_message=str(exc)[:1000]
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            _current_span_id.reset(span_token)
            _current_trace_id.reset(trace_token)
            self.client.send_span(
                trace_id=span.trace_id,
                span_id=span.span_id,
                parent_id=span.parent_id,
                name=span.name,
                start_time=start_wall,
                end_time=datetime.now(timezone.utc),
                duration_ms=round(duration_ms, 3),
                metadata=span.metadata,
            )
