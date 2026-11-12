"""GET traces, GET single trace with full span tree."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import get_session
from src.services.trace_service import TraceService


router = APIRouter()


def get_trace_service(
    session: AsyncSession = Depends(get_session),
) -> TraceService:
    return TraceService(session=session)


@router.get("/")
async def list_traces(
    limit: int = 50,
    trace_service: TraceService = Depends(get_trace_service),
):
    """List traces with optional pagination."""
    return await trace_service.list_traces(limit=limit)


@router.get("/{trace_id}")
async def get_trace(
    trace_id: str,
    trace_service: TraceService = Depends(get_trace_service),
):
    """Get a single trace with its full span tree."""
    trace = await trace_service.get_trace_with_spans(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
