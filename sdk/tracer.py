"""`with tracer.span("tool_call"): ...` context manager."""

from contextlib import contextmanager
from typing import Iterator


class Tracer:
    """Context manager for creating spans."""

    def __init__(self, client):
        self.client = client

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        """Create a span with the given name."""
        start = __import__("time").time()
        try:
            yield
        finally:
            duration = (__import__("time").time() - start) * 1000
            self.client.send_span(name=name, duration_ms=duration)
