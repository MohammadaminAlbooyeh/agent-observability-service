"""Span/trace Pydantic models (OpenTelemetry-style)."""

from typing import Any, Optional

from pydantic import BaseModel


class SpanCreate(BaseModel):
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = {}


class SpanRead(SpanCreate):
    id: str


class TraceCreate(BaseModel):
    trace_id: str
    name: str
    metadata: dict[str, Any] = {}


class TraceRead(BaseModel):
    id: str
    trace_id: str
    name: str
    spans: list[SpanRead] = []
    metadata: dict[str, Any] = {}
