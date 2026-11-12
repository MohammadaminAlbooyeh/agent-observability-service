"""Stored alert conditions."""

from pydantic import BaseModel


class AlertRule(BaseModel):
    id: str
    name: str
    metric: str
    threshold: float
    operator: str
    enabled: bool = True
