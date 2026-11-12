"""LLM-as-judge scores per trace."""

from pydantic import BaseModel


class Evaluation(BaseModel):
    id: str
    trace_id: str
    judge: str
    score: float
    rationale: str
    created_at: str = ""
