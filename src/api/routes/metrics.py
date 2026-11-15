"""Aggregated latency/cost/error-rate endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.metric import CostSummary, ErrorRate, LatencyPercentiles, MetricsSummary
from src.database.base import get_session
from src.services.metrics_service import MetricFilter, MetricsService

router = APIRouter()


def metric_filter(
    project_id: Optional[str] = None,
    window_minutes: Optional[int] = Query(
        None, ge=1, description="Only traces created in the last N minutes"
    ),
) -> MetricFilter:
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=window_minutes) if window_minutes else None
    )
    return MetricFilter(project_id=project_id, since=since)


@router.get("/summary", response_model=MetricsSummary)
async def summary(
    flt: MetricFilter = Depends(metric_filter), session: AsyncSession = Depends(get_session)
):
    return await MetricsService(session).snapshot(flt)


@router.get("/latency", response_model=LatencyPercentiles)
async def latency(
    flt: MetricFilter = Depends(metric_filter), session: AsyncSession = Depends(get_session)
):
    """p50/p95/p99 end-to-end trace latency (root span duration)."""
    return await MetricsService(session).latency_percentiles(flt)


@router.get("/cost", response_model=CostSummary)
async def cost(
    flt: MetricFilter = Depends(metric_filter), session: AsyncSession = Depends(get_session)
):
    return await MetricsService(session).cost_summary(flt)


@router.get("/error-rate", response_model=ErrorRate)
async def error_rate(
    flt: MetricFilter = Depends(metric_filter), session: AsyncSession = Depends(get_session)
):
    """Percentage of traces with at least one errored span."""
    return await MetricsService(session).error_rate(flt)
