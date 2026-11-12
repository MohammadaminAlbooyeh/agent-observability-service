"""Endpoint that external agents POST traces/spans to."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware import auth
from src.api.schemas.trace import SpanCreate
from src.database.base import get_session
from src.services.trace_service import TraceService


router = APIRouter()


def get_trace_service(
    session: AsyncSession = Depends(get_session),
) -> TraceService:
    return TraceService(session=session)


@router.post("/trace")
async def receive_trace(
    span: SpanCreate,
    trace_service: TraceService = Depends(get_trace_service),
    _: None = Depends(auth.verify_api_key),
):
    """Accept a single span from an external agent."""
    try:
        return await trace_service.create_span(span)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
