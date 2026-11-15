"""Span/trace Pydantic models (OpenTelemetry-style)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SpanCreate(BaseModel):
    trace_id: str = Field(min_length=1, max_length=64)
    span_id: str = Field(min_length=1, max_length=64)
    parent_id: Optional[str] = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    start_time: datetime = Field(description="ISO-8601 string or unix timestamp (seconds)")
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
