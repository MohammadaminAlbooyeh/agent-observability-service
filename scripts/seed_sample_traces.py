"""Populates fake traces for local dashboard testing."""

import asyncio
from datetime import datetime, timedelta, timezone


from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import (
    Project,
    Span,
    Trace,
)


SAMPLE_TRACES = [
    {
        "trace_id": f"trace-{i:04d}",
        "name": f"sample-trace-{i}",
        "spans": [
            {
                "span_id": f"span-{i:04d}-root",
                "parent_id": None,
                "name": "llm_call",
                "duration_ms": 1200.0 + (i * 10),
                "metadata": {"model": "gpt-4", "tokens": 250},
            },
            {
                "span_id": f"span-{i:04d}-tool",
                "parent_id": f"span-{i:04d}-root",
                "name": "tool_call",
                "duration_ms": 450.0 + (i * 5),
                "metadata": {"tool": "web_search"},
            },
        ],
    }
    for i in range(1, 6)
]


async def main() -> None:
    """Seed sample traces, spans, and a project into the database."""
    async with AsyncSessionLocal() as session:
        project = Project(name="sample-app", team="platform")
        session.add(project)
        await session.flush()

        for trace_data in SAMPLE_TRACES:
            trace = Trace(
                trace_id=trace_data["trace_id"],
                name=trace_data["name"],
                project_id=project.id,
            )
            session.add(trace)
            await session.flush()

            for span_data in trace_data["spans"]:
                start = datetime.now(timezone.utc) - timedelta(minutes=10)
                end = start + timedelta(milliseconds=span_data["duration_ms"])
                span = Span(
                    trace_id=trace.id,
                    span_id=span_data["span_id"],
                    parent_id=span_data["parent_id"],
                    name=span_data["name"],
                    start_time=start,
                    end_time=end,
                    duration_ms=span_data["duration_ms"],
                    metadata=span_data["metadata"],
                )
                session.add(span)

        await session.commit()
        print(f"Seeded {len(SAMPLE_TRACES)} sample traces into project '{project.name}'.")
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
