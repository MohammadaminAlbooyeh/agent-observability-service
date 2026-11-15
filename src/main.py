"""FastAPI app entrypoint for agent-observability-service."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.middleware import error_handler
from src.api.middleware.auth import require_admin
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.routes import alerts, auth, comparisons, metrics, projects, traces
from src.config.logging import setup_logging
from src.config.settings import settings
from src.dashboard.views import router as dashboard_router
from src.database.base import AsyncSessionLocal
from src.ingestion.trace_receiver import router as ingestion_router
from src.services.alert_service import AlertService

setup_logging()
logger = logging.getLogger(__name__)


async def _alert_scheduler(interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionLocal() as session:
                results = await AlertService(session).evaluate_all()
            fired = sum(r["notified"] for r in results)
            if fired:
                logger.info("Alert evaluation: %d rule(s) notified", fired)
        except Exception:  # keep the scheduler alive across transient DB/network errors
            logger.exception("Alert evaluation failed")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not settings.admin_api_keys:
        logger.warning("ADMIN_API_KEYS is empty: admin API and dashboard login are disabled")
    task = None
    if settings.alert_eval_interval_seconds > 0:
        task = asyncio.create_task(_alert_scheduler(settings.alert_eval_interval_seconds))
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Agent Observability Service",
    description="Trace, span, and evaluation ingestion and query service for AI agents.",
    version="0.2.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "ingestion", "description": "Span ingestion (project API key)"},
        {"name": "auth", "description": "Exchange an admin key for a JWT"},
        {"name": "traces", "description": "Trace retrieval and evaluation (admin)"},
        {"name": "metrics", "description": "Latency, cost, and error-rate metrics (admin)"},
        {"name": "comparisons", "description": "Version comparisons (admin)"},
        {"name": "alerts", "description": "Alert rules and evaluation (admin)"},
        {"name": "projects", "description": "Projects and their ingestion keys (admin)"},
        {"name": "dashboard", "description": "Server-rendered dashboard"},
        {"name": "health", "description": "Health check"},
    ],
)

# Starlette runs the last-added middleware first; RequestID must wrap everything.
app.add_middleware(
    RateLimitMiddleware,
    calls=settings.rate_limit_calls,
    period=settings.rate_limit_period_seconds,
)
app.add_middleware(RequestIDMiddleware)
error_handler.register_exception_handlers(app)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "dashboard" / "static"),
    name="static",
)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


admin = [Depends(require_admin)]
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(traces.router, prefix="/traces", tags=["traces"], dependencies=admin)
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"], dependencies=admin)
app.include_router(
    comparisons.router, prefix="/comparisons", tags=["comparisons"], dependencies=admin
)
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"], dependencies=admin)
app.include_router(projects.router, prefix="/projects", tags=["projects"], dependencies=admin)
app.include_router(dashboard_router, tags=["dashboard"])
