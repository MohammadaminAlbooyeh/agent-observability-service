"""Compare two prompt/model versions side by side."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import get_session
from src.services.comparison_service import ComparisonService


router = APIRouter()


def get_comparison_service(
    session: AsyncSession = Depends(get_session),
) -> ComparisonService:
    return ComparisonService(session=session)


@router.get("/{version_a}/{version_b}")
async def compare_versions(
    version_a: str,
    version_b: str,
    comparison_service: ComparisonService = Depends(get_comparison_service),
):
    """Diff metrics between two versions/tags."""
    return await comparison_service.compare(version_a, version_b)
