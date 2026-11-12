"""Aggregated latency/cost/error-rate endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import get_session
from src.services.metrics_service import MetricsService


router = APIRouter()


def get_metrics_service(
    session: AsyncSession = Depends(get_session),
) -> MetricsService:
    return MetricsService(session=session)


@router.get("/latency")
async def latency(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    """Return p50/p95 latency metrics."""
    return await metrics_service.latency_percentiles()


@router.get("/cost")
async def cost(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    """Return cost per trace aggregated metrics."""
    return await metrics_service.cost_summary()


@router.get("/error-rate")
async def error_rate(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    """Return aggregated error rate."""
    return await metrics_service.error_rate()
