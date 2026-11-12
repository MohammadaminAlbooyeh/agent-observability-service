"""CRUD for alert rules (e.g. error rate > X%)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.alert import AlertRuleCreate, AlertRuleRead
from src.database.base import get_session
from src.services.alert_service import AlertService


router = APIRouter()


def get_alert_service(
    session: AsyncSession = Depends(get_session),
) -> AlertService:
    return AlertService(session=session)


@router.post("/", response_model=AlertRuleRead)
async def create_alert_rule(
    rule: AlertRuleCreate,
    alert_service: AlertService = Depends(get_alert_service),
):
    """Create a new alert rule."""
    return await alert_service.create_rule(rule)


@router.get("/")
async def list_alert_rules(
    alert_service: AlertService = Depends(get_alert_service),
):
    """List all alert rules."""
    return await alert_service.list_rules()


@router.get("/{rule_id}", response_model=AlertRuleRead)
async def get_alert_rule(
    rule_id: str,
    alert_service: AlertService = Depends(get_alert_service),
):
    """Get a single alert rule by ID."""
    rule = await alert_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule
