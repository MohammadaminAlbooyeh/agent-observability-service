"""Logical grouping of traces (per application/team)."""

from pydantic import BaseModel


class Project(BaseModel):
    id: str
    name: str
    team: str = ""
    created_at: str = ""
