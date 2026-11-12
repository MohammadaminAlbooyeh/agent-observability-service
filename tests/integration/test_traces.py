"""Integration tests for trace ingestion and retrieval."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.api.schemas.trace import SpanCreate
from src.database.models.sqlalchemy_models import Trace
from src.services.trace_service import TraceService


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_create_span_creates_trace_and_span(db_session):
    service = TraceService(session=db_session)

    span = SpanCreate(
        trace_id="trace-abc-123",
        span_id="span-1",
        parent_id=None,
        name="llm_call",
        start_time=_now_iso(),
        end_time=_now_iso(),
        duration_ms=150.5,
        metadata={"model": "gpt-4"},
    )
    result = await service.create_span(span)

    assert result["trace_id"] == "trace-abc-123"
    assert result["span_id"] == "span-1"
    assert result["name"] == "llm_call"
    assert result["duration_ms"] == 150.5
    assert result["metadata"] == {"model": "gpt-4"}

    # Verify persisted in DB
    stmt = select(Trace).where(Trace.trace_id == "trace-abc-123")
    trace_row = (await db_session.execute(stmt)).scalar_one()
    assert trace_row.name == "llm_call"


@pytest.mark.asyncio
async def test_create_span_reuses_existing_trace(db_session):
    service = TraceService(session=db_session)

    span1 = SpanCreate(
        trace_id="trace-reuse",
        span_id="span-a",
        parent_id=None,
        name="root",
        start_time=_now_iso(),
        duration_ms=100.0,
    )
    await service.create_span(span1)

    span2 = SpanCreate(
        trace_id="trace-reuse",
        span_id="span-b",
        parent_id="span-a",
        name="child",
        start_time=_now_iso(),
        duration_ms=50.0,
    )
    result = await service.create_span(span2)

    assert result["trace_id"] == "trace-reuse"
    assert result["parent_id"] == "span-a"


@pytest.mark.asyncio
async def test_list_traces(db_session):
    service = TraceService(session=db_session)

    for i in range(3):
        await service.create_span(
            SpanCreate(
                trace_id=f"trace-list-{i}",
                span_id=f"span-list-{i}",
                parent_id=None,
                name=f"span-{i}",
                start_time=_now_iso(),
                duration_ms=10.0 * i,
            )
        )

    traces = await service.list_traces(limit=10)
    assert len(traces) == 3


@pytest.mark.asyncio
async def test_get_trace_with_spans(db_session):
    service = TraceService(session=db_session)

    await service.create_span(
        SpanCreate(
            trace_id="trace-tree",
            span_id="span-root",
            parent_id=None,
            name="root",
            start_time=_now_iso(),
            duration_ms=100.0,
        )
    )
    await service.create_span(
        SpanCreate(
            trace_id="trace-tree",
            span_id="span-child",
            parent_id="span-root",
            name="child",
            start_time=_now_iso(),
            duration_ms=50.0,
        )
    )

    trace = await service.get_trace_with_spans("trace-tree")
    assert trace is not None
    assert trace["trace_id"] == "trace-tree"
    assert len(trace["spans"]) == 2
    span_names = {s["name"] for s in trace["spans"]}
    assert span_names == {"root", "child"}


@pytest.mark.asyncio
async def test_get_trace_with_spans_not_found(db_session):
    service = TraceService(session=db_session)
    result = await service.get_trace_with_spans("nonexistent")
    assert result is None
