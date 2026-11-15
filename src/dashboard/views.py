"""Server-rendered dashboard (login with an admin API key; session is a JWT cookie)."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DASHBOARD_COOKIE,
    create_access_token,
    dashboard_user,
    is_admin_key,
)
from src.config.settings import settings
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project
from src.services.metrics_service import MetricFilter, MetricsService
from src.services.trace_service import TraceService

router = APIRouter(prefix="/dashboard")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _to_login() -> RedirectResponse:
    return RedirectResponse("/dashboard/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, api_key: str = Form(...)):
    if not is_admin_key(api_key):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid admin API key"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        DASHBOARD_COOKIE,
        create_access_token("admin"),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


@router.post("/logout")
async def logout():
    response = _to_login()
    response.delete_cookie(DASHBOARD_COOKIE)
    return response


@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    project_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    if not dashboard_user(request):
        return _to_login()
    flt = MetricFilter(project_id=project_id or None)
    projects = (await session.execute(select(Project).order_by(Project.name))).scalars().all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "traces": await TraceService(session).list_traces(limit=50, project_id=flt.project_id),
            "metrics": await MetricsService(session).snapshot(flt),
            "projects": projects,
            "project_id": project_id or "",
        },
    )


@router.get("/traces/{trace_id}", response_class=HTMLResponse)
async def trace_detail(
    request: Request, trace_id: str, session: AsyncSession = Depends(get_session)
):
    if not dashboard_user(request):
        return _to_login()
    trace = await TraceService(session).get_trace_with_spans(trace_id)
    if trace is None:
        return templates.TemplateResponse(
            "not_found.html", {"request": request}, status_code=status.HTTP_404_NOT_FOUND
        )
    return templates.TemplateResponse("trace_detail.html", {"request": request, "trace": trace})
