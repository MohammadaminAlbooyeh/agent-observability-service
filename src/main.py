"""FastAPI app entrypoint for agent-observability-service."""

from fastapi import FastAPI

from src.api.middleware import auth, error_handler
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.routes import comparisons, alerts, metrics, projects, traces
from src.config.logging import setup_logging
from src.config.settings import settings
from src.database.base import init_db
from src.dashboard.views import router as dashboard_router
from src.ingestion.batch_ingest import router as batch_ingest_router
from src.ingestion.trace_receiver import router as trace_receiver_router


setup_logging()

app = FastAPI(
    title="Agent Observability Service",
    description="Trace, span, and evaluation ingestion and query service for AI agents.",
    version="0.1.0",
    openapi_tags=[
        {"name": "traces", "description": "Trace and span ingestion and retrieval"},
        {"name": "ingestion", "description": "Agent trace/span ingestion endpoints"},
        {"name": "metrics", "description": "Aggregated latency, cost, and error-rate metrics"},
        {"name": "comparisons", "description": "Side-by-side version/tag comparisons"},
        {"name": "alerts", "description": "Alert rule CRUD and evaluation"},
        {"name": "projects", "description": "Project (application/team) management"},
        {"name": "dashboard", "description": "Server-rendered dashboard views"},
        {"name": "health", "description": "Health check"},
    ],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60.0)
error_handler.register_exception_handlers(app)


@app.on_event("startup")
async def startup() -> None:
    """Initialize database connections and middleware on startup."""
    await init_db()
    auth.configure_api_keys(settings)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


app.include_router(traces.router, prefix="/traces", tags=["traces"])
app.include_router(
    trace_receiver_router, prefix="/ingestion", tags=["ingestion"]
)
app.include_router(
    batch_ingest_router, prefix="/ingestion", tags=["ingestion"]
)
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(comparisons.router, prefix="/comparisons", tags=["comparisons"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(dashboard_router, tags=["dashboard"])
