"""Compare two versions (the `version` key in span metadata) side by side."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.metrics import metric_filter
from src.database.base import get_session
from src.services.comparison_service import ComparisonService
from src.services.metrics_service import MetricFilter

router = APIRouter()


@router.get("/{version_a}/{version_b}")
async def compare_versions(
    version_a: str,
    version_b: str,
    flt: MetricFilter = Depends(metric_filter),
    session: AsyncSession = Depends(get_session),
):
    """Metrics for each version plus the diff (b - a)."""
    return await ComparisonService(session).compare(
        version_a, version_b, project_id=flt.project_id, since=flt.since
    )
