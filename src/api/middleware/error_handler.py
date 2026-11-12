"""Global error handler middleware."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


async def error_handler_middleware(request: Request, call_next):
    """Catch unhandled exceptions and return a JSON error response."""
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the error handler middleware on the app."""
    app.middleware("http")(error_handler_middleware)
