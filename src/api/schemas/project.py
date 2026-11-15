"""Project Pydantic schemas."""

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    team: str = Field(default="", max_length=255)


class ProjectRead(ProjectCreate):
    id: str
    created_at: str


class ProjectWithKey(ProjectRead):
    api_key: str = Field(description="Ingestion API key. Shown only once; store it securely.")
