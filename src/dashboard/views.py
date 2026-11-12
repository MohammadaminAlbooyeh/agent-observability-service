"""Server-rendered dashboard views."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.services.trace_service import TraceService
from src.database.base import AsyncSessionLocal

router = APIRouter()
templates = Jinja2Templates(directory="src/dashboard/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the observability dashboard with recent traces."""
    async with AsyncSessionLocal() as session:
        service = TraceService(session=session)
        traces = await service.list_traces(limit=20)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "traces": traces},
    )


@router.get("/dashboard/traces/{trace_id}", response_class=HTMLResponse)
async def trace_detail(request: Request, trace_id: str):
    """Render a single trace with its span tree."""
    async with AsyncSessionLocal() as session:
        service = TraceService(session=session)
        trace = await service.get_trace_with_spans(trace_id)
    if trace is None:
        return HTMLResponse("<h1>Trace not found</h1>", status_code=404)
    return templates.TemplateResponse(
        "trace_detail.html",
        {"request": request, "trace": trace},
    )
