"""Diffs metrics between two versions (the `version` key in span metadata)."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics_service import MetricFilter, MetricsService

COMPARED_METRICS = ("total_traces", "p50_ms", "p95_ms", "error_rate", "average_cost_per_trace_usd")


class ComparisonService:
    def __init__(self, session: AsyncSession):
        self.metrics = MetricsService(session)

    async def compare(
        self,
        version_a: str,
        version_b: str,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        stats = {}
        for version in (version_a, version_b):
            snap = await self.metrics.snapshot(MetricFilter(project_id, since, version))
            stats[version] = {"version": version, **{m: snap[m] for m in COMPARED_METRICS}}
        a, b = stats[version_a], stats[version_b]
        return {
            "version_a": a,
            "version_b": b,
            "diff": {m: round(b[m] - a[m], 6) for m in COMPARED_METRICS},
        }
