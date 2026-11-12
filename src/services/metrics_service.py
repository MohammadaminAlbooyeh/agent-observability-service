"""Computes p50/p95 latency, cost per trace, error rate."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import Span, Trace


class MetricsService:
    """Service for computing aggregated metrics from stored traces/spans."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return AsyncSessionLocal()

    async def latency_percentiles(self) -> dict[str, Any]:
        """Return p50/p95/p99 latency from completed spans."""
        session = await self._get_session()
        result = await session.execute(
            select(Span.duration_ms).where(Span.duration_ms.is_not(None))
        )
        durations = sorted([row[0] for row in result.all()])
        if self._session is None:
            await session.close()
        if not durations:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}

        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * (p / 100.0)
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[f]
            d0 = data[f] * (c - k)
            d1 = data[c] * (k - f)
            return d0 + d1

        return {
            "p50_ms": round(percentile(durations, 50), 2),
            "p95_ms": round(percentile(durations, 95), 2),
            "p99_ms": round(percentile(durations, 99), 2),
        }

    async def cost_summary(self) -> dict[str, Any]:
        """Return cost summary aggregated from trace metadata."""
        session = await self._get_session()
        result = await session.execute(select(Trace.trace_metadata))
        traces = result.scalars().all()
        if self._session is None:
            await session.close()
        total_cost = 0.0
        trace_count = len(traces)
        for metadata in traces:
            if isinstance(metadata, dict):
                total_cost += float(metadata.get("cost_usd", 0.0))
        avg_cost = total_cost / trace_count if trace_count else 0.0
        return {
            "total_cost_usd": round(total_cost, 4),
            "average_cost_per_trace_usd": round(avg_cost, 4),
        }

    async def error_rate(self) -> dict[str, Any]:
        """Return aggregated error rate from trace metadata."""
        session = await self._get_session()
        result = await session.execute(select(Trace.trace_metadata))
        traces = result.scalars().all()
        if self._session is None:
            await session.close()
        total = len(traces)
        errors = 0
        for metadata in traces:
            if isinstance(metadata, dict) and metadata.get("error"):
                errors += 1
        rate = (errors / total * 100.0) if total else 0.0
        return {
            "error_rate": round(rate, 2),
            "total_traces": total,
            "error_traces": errors,
        }
