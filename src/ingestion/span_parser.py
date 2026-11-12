"""Validates and normalizes incoming span data."""

from typing import Any, Optional

from pydantic import BaseModel


class NormalizedSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = {}


def normalize_span(raw: dict) -> NormalizedSpan:
    """Normalize an OpenTelemetry-style span payload into a canonical model."""
    return NormalizedSpan(
        trace_id=raw.get("trace_id", ""),
        span_id=raw.get("span_id", ""),
        parent_id=raw.get("parent_id"),
        name=raw.get("name", ""),
        start_time=raw.get("start_time", ""),
        end_time=raw.get("end_time"),
        duration_ms=raw.get("duration_ms"),
        metadata=raw.get("metadata", {}),
    )
