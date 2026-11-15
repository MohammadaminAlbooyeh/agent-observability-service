"""Stores/retrieves traces and builds span trees."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import case, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.trace import SpanCreate
from src.database.models.sqlalchemy_models import Span as SpanModel
from src.database.models.sqlalchemy_models import Trace as TraceModel
from src.evaluators.cost_calculator import CostCalculator


class TraceOwnershipError(Exception):
    """A span targets a trace that belongs to a different project."""


class IngestConflictError(Exception):
    """A concurrent write created the same trace/span; the client should retry."""


_cost_calculator = CostCalculator()


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return _utc(dt).isoformat() if dt else None


def _is_error(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("error")) or str(metadata.get("status", "")).lower() == "error"


def _cost(metadata: dict[str, Any]) -> Optional[float]:
    if isinstance(metadata.get("cost_usd"), (int, float)):
        return float(metadata["cost_usd"])
    model = metadata.get("model")
    input_tokens = metadata.get("input_tokens", metadata.get("prompt_tokens"))
    output_tokens = metadata.get("output_tokens", metadata.get("completion_tokens"))
    if model and isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return _cost_calculator.calculate(model, input_tokens, output_tokens)["total_cost_usd"]
    return None


def serialize_span(s: SpanModel) -> dict[str, Any]:
    return {
        "id": s.id,
        "span_id": s.span_id,
        "parent_id": s.parent_id,
        "name": s.name,
        "start_time": _iso(s.start_time),
        "end_time": _iso(s.end_time),
        "duration_ms": s.duration_ms,
        "cost_usd": s.cost_usd,
        "error": s.error,
        "metadata": s.span_metadata,
    }


def build_span_tree(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Nest spans under their parents; spans with unknown parents become roots."""
    nodes = {s["span_id"]: {**s, "children": []} for s in spans}
    roots = []
    for span in spans:
        node = nodes[span["span_id"]]
        parent = nodes.get(span["parent_id"]) if span["parent_id"] else None
        (parent["children"] if parent else roots).append(node)
    return roots


class TraceService:
    """Trace and span persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_span(self, span: SpanCreate, project_id: Optional[str] = None) -> dict:
        return (await self.ingest_spans([span], project_id=project_id))[0]

    async def ingest_spans(
        self, spans: list[SpanCreate], project_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Persist spans in a single transaction. Re-sent spans are returned, not duplicated.

        ``project_id=None`` means an admin ingest, which may write to any trace.
        """
        traces: dict[str, TraceModel] = {}
        seen: dict[tuple[str, str], SpanModel] = {}
        results: list[SpanModel] = []
        try:
            for span in spans:
                trace = traces.get(span.trace_id) or await self._get_or_create_trace(
                    span, project_id
                )
                traces[span.trace_id] = trace

                key = (span.trace_id, span.span_id)
                existing = seen.get(key) or await self._find_span(trace.id, span.span_id)
                if existing is not None:
                    seen[key] = existing
                    results.append(existing)
                    continue

                db_span = self._build_span(trace, span)
                self.session.add(db_span)
                seen[key] = db_span
                results.append(db_span)
                self._update_trace_from_span(trace, span)

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise IngestConflictError(str(exc.orig)) from exc
        except Exception:
            await self.session.rollback()
            raise

        return [
            {**serialize_span(db_span), "trace_id": span.trace_id}
            for span, db_span in zip(spans, results)
        ]

    async def _get_or_create_trace(
        self, span: SpanCreate, project_id: Optional[str]
    ) -> TraceModel:
        result = await self.session.execute(
            select(TraceModel).where(TraceModel.trace_id == span.trace_id)
        )
        trace = result.scalar_one_or_none()
        if trace is not None:
            if project_id is not None and trace.project_id != project_id:
                raise TraceOwnershipError(f"Trace {span.trace_id} belongs to another project")
            return trace

        trace = TraceModel(
            trace_id=span.trace_id,
            name=span.name,
            version=span.metadata.get("version"),
            trace_metadata=dict(span.metadata),
            project_id=project_id,
        )
        self.session.add(trace)
        await self.session.flush()
        return trace

    async def _find_span(self, trace_pk: str, span_id: str) -> Optional[SpanModel]:
        result = await self.session.execute(
            select(SpanModel).where(SpanModel.trace_id == trace_pk, SpanModel.span_id == span_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _build_span(trace: TraceModel, span: SpanCreate) -> SpanModel:
        start, end = _utc(span.start_time), _utc(span.end_time)
        duration = span.duration_ms
        if duration is None and end is not None:
            duration = max((end - start).total_seconds() * 1000.0, 0.0)
        return SpanModel(
            trace_id=trace.id,
            span_id=span.span_id,
            parent_id=span.parent_id,
            name=span.name,
            start_time=start,
            end_time=end,
            duration_ms=duration,
            cost_usd=_cost(span.metadata),
            error=_is_error(span.metadata),
            span_metadata=dict(span.metadata),
        )

    @staticmethod
    def _update_trace_from_span(trace: TraceModel, span: SpanCreate) -> None:
        if trace.version is None and span.metadata.get("version"):
            trace.version = str(span.metadata["version"])
        if span.parent_id is None:
            trace.name = span.name
            trace.trace_metadata = {**(trace.trace_metadata or {}), **span.metadata}

    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        project_id: Optional[str] = None,
        version: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List traces (most recent first) with span count, error flag, and total cost."""
        stats = (
            select(
                SpanModel.trace_id.label("trace_pk"),
                func.count(SpanModel.id).label("span_count"),
                func.max(case((SpanModel.error.is_(True), 1), else_=0)).label("has_error"),
                func.coalesce(func.sum(SpanModel.cost_usd), 0.0).label("cost_usd"),
            )
            .group_by(SpanModel.trace_id)
            .subquery()
        )
        stmt = (
            select(TraceModel, stats.c.span_count, stats.c.has_error, stats.c.cost_usd)
            .outerjoin(stats, stats.c.trace_pk == TraceModel.id)
            .order_by(desc(TraceModel.created_at), desc(TraceModel.id))
            .limit(limit)
            .offset(offset)
        )
        if project_id:
            stmt = stmt.where(TraceModel.project_id == project_id)
        if version:
            stmt = stmt.where(TraceModel.version == version)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "id": t.id,
                "trace_id": t.trace_id,
                "name": t.name,
                "version": t.version,
                "project_id": t.project_id,
                "metadata": t.trace_metadata,
                "created_at": _iso(t.created_at),
                "span_count": span_count or 0,
                "error": bool(has_error),
                "cost_usd": round(cost or 0.0, 6),
            }
            for t, span_count, has_error, cost in rows
        ]

    async def get_trace_with_spans(
        self, trace_id: str, project_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Return a trace with its spans (flat, by start time) and a nested span tree."""
        stmt = (
            select(TraceModel)
            .options(selectinload(TraceModel.spans), selectinload(TraceModel.evaluations))
            .where(TraceModel.trace_id == trace_id)
        )
        if project_id:
            stmt = stmt.where(TraceModel.project_id == project_id)
        trace = (await self.session.execute(stmt)).scalar_one_or_none()
        if trace is None:
            return None

        spans = [serialize_span(s) for s in sorted(trace.spans, key=lambda s: _utc(s.start_time))]
        return {
            "id": trace.id,
            "trace_id": trace.trace_id,
            "name": trace.name,
            "version": trace.version,
            "project_id": trace.project_id,
            "metadata": trace.trace_metadata,
            "created_at": _iso(trace.created_at),
            "error": any(s["error"] for s in spans),
            "cost_usd": round(sum(s["cost_usd"] or 0.0 for s in spans), 6),
            "spans": spans,
            "tree": build_span_tree(spans),
            "evaluations": [
                {
                    "id": e.id,
                    "judge": e.judge,
                    "score": e.score,
                    "rationale": e.rationale,
                    "created_at": _iso(e.created_at),
                }
                for e in sorted(trace.evaluations, key=lambda e: _utc(e.created_at))
            ],
        }
