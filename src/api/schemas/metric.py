"""Metric Pydantic models."""

from pydantic import BaseModel


class LatencyPercentiles(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float


class CostSummary(BaseModel):
    total_cost_usd: float
    average_cost_per_trace_usd: float


class ErrorRate(BaseModel):
    error_rate: float
    total_traces: int
    error_traces: int


class MetricsSummary(LatencyPercentiles, CostSummary, ErrorRate):
    pass
