"""Project Pydantic schemas."""

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    team: str = ""


class ProjectRead(ProjectCreate):
    id: str
    created_at: str
