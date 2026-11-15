"""Project management. Each project owns an ingestion API key."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import generate_project_api_key, hash_api_key
from src.api.schemas.project import ProjectCreate, ProjectRead, ProjectWithKey
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project

router = APIRouter()


def _read(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "team": p.team or "",
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


async def _get_or_404(session: AsyncSession, project_id: str) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/", response_model=ProjectWithKey, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate, session: AsyncSession = Depends(get_session)):
    """Create a project and return its ingestion API key (shown only once)."""
    api_key = generate_project_api_key()
    db_project = Project(name=project.name, team=project.team, api_key_hash=hash_api_key(api_key))
    session.add(db_project)
    await session.commit()
    await session.refresh(db_project)
    return {**_read(db_project), "api_key": api_key}


@router.get("/", response_model=list[ProjectRead])
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at))
    return [_read(p) for p in result.scalars()]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)):
    return _read(await _get_or_404(session, project_id))


@router.post("/{project_id}/rotate-key", response_model=ProjectWithKey)
async def rotate_project_key(project_id: str, session: AsyncSession = Depends(get_session)):
    """Issue a new ingestion key; the old key stops working immediately."""
    project = await _get_or_404(session, project_id)
    api_key = generate_project_api_key()
    project.api_key_hash = hash_api_key(api_key)
    await session.commit()
    return {**_read(project), "api_key": api_key}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a project and its alert rules. Its traces are kept but unassigned."""
    await session.delete(await _get_or_404(session, project_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
