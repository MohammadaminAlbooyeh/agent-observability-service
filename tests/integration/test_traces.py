"""Service-level tests for trace ingestion and retrieval."""

from datetime import datetime, timedelta, timezone

import pytest

from src.api.schemas.trace import SpanCreate
from src.database.models.sqlalchemy_models import Project
from src.services.trace_service import TraceOwnershipError, TraceService

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def mk(trace_id, span_id, parent_id=None, offset_ms=0, **metadata):
    start = T0 + timedelta(milliseconds=offset_ms)
    return SpanCreate(
        trace_id=trace_id,
        span_id=span_id,
        parent_id=parent_id,
        name=span_id,
        start_time=start,
        end_time=start + timedelta(milliseconds=10),
        metadata=metadata,
    )


async def _project(session, name="p") -> Project:
    project = Project(name=name, api_key_hash=name * 8)
    session.add(project)
    await session.commit()
    return project


async def test_create_span_creates_trace(db_session):
    result = await TraceService(db_session).create_span(mk("t", "root", model="gpt-4"))
    assert result["trace_id"] == "t"
    assert result["duration_ms"] == 10.0
    assert result["metadata"] == {"model": "gpt-4"}


async def test_root_span_names_trace_even_if_late(db_session):
    service = TraceService(db_session)
    await service.create_span(mk("t", "child", parent_id="root"))
    await service.create_span(mk("t", "root", output="final"))
    trace = await service.get_trace_with_spans("t")
    assert trace["name"] == "root"
    assert trace["metadata"]["output"] == "final"


async def test_duplicate_span_in_same_batch_is_ignored(db_session):
    service = TraceService(db_session)
    results = await service.ingest_spans([mk("t", "a"), mk("t", "a")])
    assert results[0]["id"] == results[1]["id"]
    assert len((await service.get_trace_with_spans("t"))["spans"]) == 1


async def test_cost_from_tokens_and_explicit_cost(db_session):
    service = TraceService(db_session)
    await service.ingest_spans(
        [
            mk("t", "a", model="gpt-4", prompt_tokens=1000, completion_tokens=0),
            mk("t", "b", cost_usd=0.25),
            mk("t", "c", model="unknown", input_tokens=10, output_tokens=10),
        ]
    )
    spans = {s["span_id"]: s for s in (await service.get_trace_with_spans("t"))["spans"]}
    assert spans["a"]["cost_usd"] == 0.03
    assert spans["b"]["cost_usd"] == 0.25
    assert spans["c"]["cost_usd"] == 0.0


async def test_error_detection(db_session):
    service = TraceService(db_session)
    await service.ingest_spans([mk("t", "a", status="ERROR"), mk("t", "b", error=False)])
    spans = {s["span_id"]: s for s in (await service.get_trace_with_spans("t"))["spans"]}
    assert spans["a"]["error"] is True
    assert spans["b"]["error"] is False


async def test_ownership_enforced_admin_unrestricted(db_session):
    p1, p2 = await _project(db_session, "a"), await _project(db_session, "b")
    service = TraceService(db_session)
    await service.create_span(mk("t", "a"), project_id=p1.id)
    with pytest.raises(TraceOwnershipError):
        await service.create_span(mk("t", "b"), project_id=p2.id)
    await service.create_span(mk("t", "c"), project_id=None)
    assert len((await service.get_trace_with_spans("t"))["spans"]) == 2


async def test_list_traces_filters_and_pagination(db_session):
    p = await _project(db_session)
    service = TraceService(db_session)
    for i in range(5):
        await service.create_span(mk(f"t{i}", "root", version="v2" if i % 2 else "v1"),
                                  project_id=p.id if i < 3 else None)
    assert len(await service.list_traces()) == 5
    assert len(await service.list_traces(project_id=p.id)) == 3
    assert {t["trace_id"] for t in await service.list_traces(version="v2")} == {"t1", "t3"}
    page = await service.list_traces(limit=2, offset=4)
    assert len(page) == 1


async def test_spans_sorted_by_start_time_and_orphans_are_roots(db_session):
    service = TraceService(db_session)
    await service.ingest_spans(
        [mk("t", "late", offset_ms=50), mk("t", "early", offset_ms=0),
         mk("t", "orphan", parent_id="missing", offset_ms=10)]
    )
    trace = await service.get_trace_with_spans("t")
    assert [s["span_id"] for s in trace["spans"]] == ["early", "orphan", "late"]
    assert {n["span_id"] for n in trace["tree"]} == {"early", "orphan", "late"}


async def test_get_missing_trace(db_session):
    assert await TraceService(db_session).get_trace_with_spans("nope") is None
