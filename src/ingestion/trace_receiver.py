"""Ingestion endpoints that agents POST spans to (authenticated by project API key)."""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import get_ingest_project
from src.api.schemas.trace import SpanCreate
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project
from src.services.trace_service import IngestConflictError, TraceOwnershipError, TraceService

MAX_BATCH_SIZE = 1000

router = APIRouter()


async def _ingest(spans: list[SpanCreate], project: Project | None, session: AsyncSession):
    try:
        return await TraceService(session).ingest_spans(
            spans, project_id=project.id if project else None
        )
    except TraceOwnershipError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
    except IngestConflictError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Concurrent write conflict; retry")


@router.post("/trace", status_code=status.HTTP_201_CREATED)
async def receive_span(
    span: SpanCreate,
    project: Project | None = Depends(get_ingest_project),
    session: AsyncSession = Depends(get_session),
):
    """Ingest a single span."""
    return (await _ingest([span], project, session))[0]


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def receive_batch(
    spans: list[SpanCreate] = Body(..., max_length=MAX_BATCH_SIZE),
    project: Project | None = Depends(get_ingest_project),
    session: AsyncSession = Depends(get_session),
):
    """Ingest up to 1000 spans atomically. Re-sent spans are deduplicated."""
    if not spans:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No spans provided")
    created = await _ingest(spans, project, session)
    return {"count": len(created), "spans": created}
