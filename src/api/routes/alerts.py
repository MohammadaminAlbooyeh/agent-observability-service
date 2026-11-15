"""Alert rule CRUD and on-demand evaluation."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.alert import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project
from src.services.alert_service import AlertService

router = APIRouter()


@router.post("/", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(rule: AlertRuleCreate, session: AsyncSession = Depends(get_session)):
    if rule.project_id and await session.get(Project, rule.project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await AlertService(session).create_rule(rule)


@router.get("/", response_model=list[AlertRuleRead])
async def list_alert_rules(
    project_id: Optional[str] = None, session: AsyncSession = Depends(get_session)
):
    return await AlertService(session).list_rules(project_id)


@router.post("/evaluate")
async def evaluate_alerts(session: AsyncSession = Depends(get_session)):
    """Evaluate all enabled rules now (also runs periodically in the background)."""
    return await AlertService(session).evaluate_all()


@router.get("/{rule_id}", response_model=AlertRuleRead)
async def get_alert_rule(rule_id: str, session: AsyncSession = Depends(get_session)):
    rule = await AlertService(session).get_rule(rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleRead)
async def update_alert_rule(
    rule_id: str, update: AlertRuleUpdate, session: AsyncSession = Depends(get_session)
):
    rule = await AlertService(session).update_rule(rule_id, update)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(rule_id: str, session: AsyncSession = Depends(get_session)):
    if not await AlertService(session).delete_rule(rule_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
