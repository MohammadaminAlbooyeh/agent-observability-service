"""Root trace record."""

from pydantic import BaseModel


class Trace(BaseModel):
    id: str
    trace_id: str
    name: str
    metadata: dict = {}
    created_at: str = ""
