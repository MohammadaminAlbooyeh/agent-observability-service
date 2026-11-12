"""Diffs metrics between two versions/tags."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import Span, Trace


class ComparisonService:
    """Service for comparing metrics across versions/tags."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return AsyncSessionLocal()

    async def _metrics_for_version(
        self, session: AsyncSession, version: str
    ) -> dict[str, Any]:
        result = await session.execute(
            select(Trace).where(Trace.trace_metadata["version"] == version)  # type: ignore[index]
        )
        traces = result.scalars().all()
        trace_ids = [t.id for t in traces]
        if not trace_ids:
            return {
                "version": version,
                "trace_count": 0,
                "avg_duration_ms": 0.0,
                "error_count": 0,
            }

        span_result = await session.execute(
            select(Span.duration_ms).where(Span.trace_id.in_(trace_ids), Span.duration_ms.is_not(None))
        )
        durations = sorted([row[0] for row in span_result.all()])
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        error_count = sum(
            1 for t in traces if (t.trace_metadata or {}).get("error")
        )

        return {
            "version": version,
            "trace_count": len(traces),
            "avg_duration_ms": round(avg_duration, 2),
            "error_count": error_count,
        }

    async def compare(self, version_a: str, version_b: str) -> dict[str, Any]:
        """Diff metrics between two versions/tags."""
        session = await self._get_session()
        stats_a = await self._metrics_for_version(session, version_a)
        stats_b = await self._metrics_for_version(session, version_b)
        if self._session is None:
            await session.close()

        diff = {
            "trace_count": stats_b["trace_count"] - stats_a["trace_count"],
            "avg_duration_ms": round(
                stats_b["avg_duration_ms"] - stats_a["avg_duration_ms"], 2
            ),
            "error_count": stats_b["error_count"] - stats_a["error_count"],
        }

        return {
            "version_a": stats_a,
            "version_b": stats_b,
            "diff": diff,
        }
