"""Group traces by project/application."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.project import ProjectCreate, ProjectRead
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project as ProjectModel


router = APIRouter()


@router.post("/", response_model=ProjectRead)
async def create_project(
    project: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new project."""
    db_project = ProjectModel(name=project.name, team=project.team)
    session.add(db_project)
    await session.commit()
    await session.refresh(db_project)
    return ProjectRead(
        id=str(db_project.id),
        name=db_project.name,
        team=db_project.team or "",
        created_at=db_project.created_at.isoformat() if db_project.created_at else "",
    )


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(get_session),
):
    """List all projects."""
    result = await session.execute(select(ProjectModel))
    projects = result.scalars().all()
    return [
        ProjectRead(
            id=str(p.id),
            name=p.name,
            team=p.team or "",
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single project by ID."""
    project = await session.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead(
        id=str(project.id),
        name=project.name,
        team=project.team or "",
        created_at=project.created_at.isoformat() if project.created_at else "",
    )
