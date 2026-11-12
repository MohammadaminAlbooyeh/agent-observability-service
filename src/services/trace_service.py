"""Stores/retrieves traces, builds span trees."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.trace import SpanCreate
from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import Span as SpanModel, Trace as TraceModel


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string into a timezone-aware datetime."""
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class TraceService:
    """Service for trace and span CRUD operations backed by SQLAlchemy."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return AsyncSessionLocal()

    async def create_span(self, span: SpanCreate) -> dict[str, Any]:
        """Create (or update) a trace and persist a span within it."""
        session = await self._get_session()
        # Look up existing trace by trace_id; create if absent.
        result = await session.execute(
            select(TraceModel).where(TraceModel.trace_id == span.trace_id)
        )
        trace = result.scalar_one_or_none()

        if trace is None:
            trace = TraceModel(
                trace_id=span.trace_id,
                name=span.name,
                trace_metadata=span.metadata,
            )
            session.add(trace)
            await session.flush()

        db_span = SpanModel(
            trace_id=trace.id,
            span_id=span.span_id,
            parent_id=span.parent_id,
            name=span.name,
            start_time=_parse_dt(span.start_time),
            end_time=_parse_dt(span.end_time),
            duration_ms=span.duration_ms,
            span_metadata=span.metadata,
        )
        session.add(db_span)
        await session.commit()
        await session.refresh(db_span)

        # If we created our own session, close it.
        if self._session is None:
            await session.close()

        return {
            "id": str(db_span.id),
            "trace_id": trace.trace_id,
            "span_id": db_span.span_id,
            "parent_id": db_span.parent_id,
            "name": db_span.name,
            "start_time": db_span.start_time.isoformat() if db_span.start_time else None,
            "end_time": db_span.end_time.isoformat() if db_span.end_time else None,
            "duration_ms": db_span.duration_ms,
            "metadata": db_span.span_metadata,
        }

    async def list_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        """List traces ordered by most recent first."""
        session = await self._get_session()
        result = await session.execute(
            select(TraceModel)
            .options(selectinload(TraceModel.spans))
            .order_by(desc(TraceModel.created_at))
            .limit(limit)
        )
        traces = result.scalars().all()
        data = [
            {
                "id": str(t.id),
                "trace_id": t.trace_id,
                "name": t.name,
                "metadata": t.trace_metadata,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "span_count": len(t.spans),
            }
            for t in traces
        ]
        if self._session is None:
            await session.close()
        return data

    async def get_trace_with_spans(self, trace_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a trace with its full span tree ordered by start_time."""
        session = await self._get_session()
        result = await session.execute(
            select(TraceModel)
            .options(selectinload(TraceModel.spans))
            .where(TraceModel.trace_id == trace_id)
        )
        trace = result.scalar_one_or_none()
        if trace is None:
            if self._session is None:
                await session.close()
            return None

        spans = sorted(
            trace.spans,
            key=lambda s: s.start_time if s.start_time else "",
        )
        data = {
            "id": str(trace.id),
            "trace_id": trace.trace_id,
            "name": trace.name,
            "metadata": trace.trace_metadata,
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
            "spans": [
                {
                    "id": str(s.id),
                    "span_id": s.span_id,
                    "parent_id": s.parent_id,
                    "name": s.name,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms,
                    "metadata": s.span_metadata,
                }
                for s in spans
            ],
        }
        if self._session is None:
            await session.close()
        return data
