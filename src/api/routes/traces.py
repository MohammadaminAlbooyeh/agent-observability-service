"""List traces, get a trace with its span tree, and evaluate traces."""

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import get_session
from src.services.evaluation_service import EvaluationRequest, EvaluationService
from src.services.trace_service import TraceService

router = APIRouter()


@router.get("/")
async def list_traces(
    project_id: Optional[str] = None,
    version: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await TraceService(session).list_traces(
        limit=limit, offset=offset, project_id=project_id, version=version
    )


@router.get("/{trace_id}")
async def get_trace(trace_id: str, session: AsyncSession = Depends(get_session)):
    """Get a trace with its spans (flat), nested span tree, and evaluations."""
    trace = await TraceService(session).get_trace_with_spans(trace_id)
    if trace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return trace


@router.post("/{trace_id}/evaluate", status_code=status.HTTP_201_CREATED)
async def evaluate_trace(
    trace_id: str,
    request: Optional[EvaluationRequest] = Body(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Score a trace with rule-based checks and the LLM judge (if configured)."""
    result = await EvaluationService(session).evaluate_trace(trace_id, request)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return result
