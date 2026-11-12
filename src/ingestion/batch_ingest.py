"""Handles bulk trace uploads for high-throughput agents."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.trace import SpanCreate
from src.database.base import get_session
from src.services.trace_service import TraceService


router = APIRouter()


def get_trace_service(
    session: AsyncSession = Depends(get_session),
) -> TraceService:
    return TraceService(session=session)


@router.post("/batch")
async def ingest_batch(
    spans: List[SpanCreate],
    trace_service: TraceService = Depends(get_trace_service),
):
    """Bulk insert multiple spans in one request."""
    if not spans:
        raise HTTPException(status_code=400, detail="No spans provided")

    created = []
    for span in spans:
        try:
            created.append(await trace_service.create_span(span))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return {"count": len(created), "spans": created}
