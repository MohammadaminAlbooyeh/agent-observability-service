"""Individual span (parent_id, name, duration, metadata)."""

from typing import Any, Optional

from pydantic import BaseModel


class Span(BaseModel):
    id: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = {}
