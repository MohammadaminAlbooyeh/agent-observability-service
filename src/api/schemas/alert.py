"""Alert Pydantic models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MetricName = Literal[
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "total_cost_usd",
    "average_cost_per_trace_usd",
    "error_rate",
    "total_traces",
    "error_traces",
]
Operator = Literal[">", "<", ">=", "<=", "=="]


def _validate_channel(value: Optional[str]) -> Optional[str]:
    if value in (None, "", "log"):
        return value or None
    if value.startswith(("http://", "https://")):
        return value
    raise ValueError("channel must be 'log' or an http(s) webhook URL (e.g. a Slack webhook)")


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    metric: MetricName
    threshold: float
    operator: Operator
    window_minutes: int = Field(default=60, ge=1, le=60 * 24 * 30)
    channel: Optional[str] = Field(default=None, max_length=1024)
    project_id: Optional[str] = None
    enabled: bool = True

    _check_channel = field_validator("channel")(_validate_channel)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    metric: Optional[MetricName] = None
    threshold: Optional[float] = None
    operator: Optional[Operator] = None
    window_minutes: Optional[int] = Field(default=None, ge=1, le=60 * 24 * 30)
    channel: Optional[str] = Field(default=None, max_length=1024)
    enabled: Optional[bool] = None

    _check_channel = field_validator("channel")(_validate_channel)


class AlertRuleRead(AlertRuleCreate):
    id: str
    last_triggered_at: Optional[str] = None
