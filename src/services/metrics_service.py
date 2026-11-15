"""Computes latency percentiles, cost, and error rate over traces.

Latency is end-to-end trace latency: the duration of root spans (no parent).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.sqlalchemy_models import Span, Trace

METRIC_NAMES = (
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "total_cost_usd",
    "average_cost_per_trace_usd",
    "error_rate",
    "total_traces",
    "error_traces",
)


@dataclass
class MetricFilter:
    project_id: Optional[str] = None
    since: Optional[datetime] = None
    version: Optional[str] = None

    def apply(self, stmt: Select) -> Select:
        if self.project_id:
            stmt = stmt.where(Trace.project_id == self.project_id)
        if self.since:
            stmt = stmt.where(Trace.created_at >= self.since)
        if self.version:
            stmt = stmt.where(Trace.version == self.version)
        return stmt


def percentile(sorted_data: list[float], p: float) -> float:
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = int(k)
    if f + 1 >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[f + 1] - sorted_data[f]) * (k - f)


class MetricsService:
    """Aggregated metrics from stored traces/spans."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def latency_percentiles(self, flt: MetricFilter | None = None) -> dict[str, float]:
        flt = flt or MetricFilter()
        stmt = flt.apply(
            select(Span.duration_ms)
            .join(Trace, Span.trace_id == Trace.id)
            .where(Span.parent_id.is_(None), Span.duration_ms.is_not(None))
        )
        durations = sorted(row[0] for row in (await self.session.execute(stmt)).all())
        return {
            "p50_ms": round(percentile(durations, 50), 2),
            "p95_ms": round(percentile(durations, 95), 2),
            "p99_ms": round(percentile(durations, 99), 2),
        }

    async def _trace_count(self, flt: MetricFilter) -> int:
        return (await self.session.execute(flt.apply(select(func.count(Trace.id))))).scalar_one()

    async def cost_summary(self, flt: MetricFilter | None = None) -> dict[str, float]:
        flt = flt or MetricFilter()
        total = (
            await self.session.execute(
                flt.apply(
                    select(func.coalesce(func.sum(Span.cost_usd), 0.0)).join(
                        Trace, Span.trace_id == Trace.id
                    )
                )
            )
        ).scalar_one()
        count = await self._trace_count(flt)
        return {
            "total_cost_usd": round(float(total), 6),
            "average_cost_per_trace_usd": round(float(total) / count, 6) if count else 0.0,
        }

    async def error_rate(self, flt: MetricFilter | None = None) -> dict[str, Any]:
        flt = flt or MetricFilter()
        errors = (
            await self.session.execute(
                flt.apply(
                    select(func.count(distinct(Span.trace_id)))
                    .join(Trace, Span.trace_id == Trace.id)
                    .where(Span.error.is_(True))
                )
            )
        ).scalar_one()
        total = await self._trace_count(flt)
        return {
            "error_rate": round(errors / total * 100.0, 2) if total else 0.0,
            "total_traces": total,
            "error_traces": errors,
        }

    async def snapshot(self, flt: MetricFilter | None = None) -> dict[str, Any]:
        """All metrics in one flat dict (keys in METRIC_NAMES)."""
        flt = flt or MetricFilter()
        return {
            **(await self.latency_percentiles(flt)),
            **(await self.cost_summary(flt)),
            **(await self.error_rate(flt)),
        }
