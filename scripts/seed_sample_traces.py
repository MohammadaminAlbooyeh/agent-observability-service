"""Populate sample traces for local dashboard testing.

Usage: python -m scripts.seed_sample_traces
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from src.api.middleware.auth import generate_project_api_key, hash_api_key
from src.api.schemas.trace import SpanCreate
from src.database.base import AsyncSessionLocal, engine
from src.database.models.sqlalchemy_models import Project
from src.services.trace_service import TraceService

TRACE_COUNT = 20


def _trace_spans(i: int, now: datetime) -> list[SpanCreate]:
    version = "v1" if i % 2 else "v2"
    failed = i % 7 == 0
    start = now - timedelta(minutes=5 * i)
    llm_ms = random.uniform(600, 1800) if version == "v1" else random.uniform(400, 1200)
    tool_ms = random.uniform(100, 500)
    trace_id = f"sample-trace-{i:04d}"
    root_id = f"{trace_id}-root"
    return [
        SpanCreate(
            trace_id=trace_id,
            span_id=root_id,
            name="agent_run",
            start_time=start,
            end_time=start + timedelta(milliseconds=llm_ms + tool_ms + 50),
            metadata={"version": version, "output": f"Answer #{i}", "status": "error" if failed else "ok"},
        ),
        SpanCreate(
            trace_id=trace_id,
            span_id=f"{trace_id}-llm",
            parent_id=root_id,
            name="llm_call",
            start_time=start + timedelta(milliseconds=10),
            end_time=start + timedelta(milliseconds=10 + llm_ms),
            metadata={"model": "gpt-4", "input_tokens": 400 + i * 10, "output_tokens": 150},
        ),
        SpanCreate(
            trace_id=trace_id,
            span_id=f"{trace_id}-tool",
            parent_id=root_id,
            name="tool_call",
            start_time=start + timedelta(milliseconds=20 + llm_ms),
            end_time=start + timedelta(milliseconds=20 + llm_ms + tool_ms),
            metadata={"tool": "web_search", "error": failed},
        ),
    ]


async def main() -> None:
    api_key = generate_project_api_key()
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        project = Project(name="sample-app", team="platform", api_key_hash=hash_api_key(api_key))
        session.add(project)
        await session.commit()

        spans = [s for i in range(1, TRACE_COUNT + 1) for s in _trace_spans(i, now)]
        await TraceService(session).ingest_spans(spans, project_id=project.id)
    await engine.dispose()
    print(f"Seeded {TRACE_COUNT} traces into project 'sample-app' ({project.id}).")
    print(f"Project ingestion API key: {api_key}")


if __name__ == "__main__":
    asyncio.run(main())
