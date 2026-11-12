"""Alert Pydantic models."""

from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    name: str
    metric: str
    threshold: float
    operator: str  # e.g. ">", "<", ">="
    enabled: bool = True


class AlertRuleRead(AlertRuleCreate):
    id: str


class AlertNotification(BaseModel):
    rule_id: str
    message: str
    severity: str = "warning"
