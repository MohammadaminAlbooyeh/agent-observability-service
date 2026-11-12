"""Evaluates alert rules against incoming metrics."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.alert import AlertRuleCreate
from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import AlertRule


class AlertService:
    """Service for managing and evaluating alert rules backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return AsyncSessionLocal()

    async def create_rule(self, rule: AlertRuleCreate) -> dict[str, Any]:
        """Create an alert rule."""
        session = await self._get_session()
        db_rule = AlertRule(
            name=rule.name,
            metric=rule.metric,
            threshold=rule.threshold,
            operator=rule.operator,
            enabled=rule.enabled,
        )
        session.add(db_rule)
        await session.commit()
        await session.refresh(db_rule)
        if self._session is None:
            await session.close()
        return {
            "id": str(db_rule.id),
            "name": db_rule.name,
            "metric": db_rule.metric,
            "threshold": db_rule.threshold,
            "operator": db_rule.operator,
            "enabled": db_rule.enabled,
        }

    async def list_rules(self) -> list[dict[str, Any]]:
        """List all alert rules."""
        session = await self._get_session()
        result = await session.execute(select(AlertRule))
        rules = result.scalars().all()
        if self._session is None:
            await session.close()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "metric": r.metric,
                "threshold": r.threshold,
                "operator": r.operator,
                "enabled": r.enabled,
            }
            for r in rules
        ]

    async def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Get a single alert rule by ID."""
        session = await self._get_session()
        rule = await session.get(AlertRule, rule_id)
        if self._session is None:
            await session.close()
        if rule is None:
            return None
        return {
            "id": str(rule.id),
            "name": rule.name,
            "metric": rule.metric,
            "threshold": rule.threshold,
            "operator": rule.operator,
            "enabled": rule.enabled,
        }

    async def evaluate_metric(self, metric: str, value: float) -> list[dict[str, Any]]:
        """Evaluate a metric value against all enabled alert rules."""
        session = await self._get_session()
        result = await session.execute(
            select(AlertRule).where(AlertRule.metric == metric, AlertRule.enabled.is_(True))
        )
        rules = result.scalars().all()
        if self._session is None:
            await session.close()
        triggered = []
        for rule in rules:
            fired = False
            if rule.operator == ">" and value > rule.threshold:
                fired = True
            elif rule.operator == "<" and value < rule.threshold:
                fired = True
            elif rule.operator == ">=" and value >= rule.threshold:
                fired = True
            elif rule.operator == "<=" and value <= rule.threshold:
                fired = True
            elif rule.operator == "==" and value == rule.threshold:
                fired = True
            if fired:
                triggered.append(
                    {
                        "rule_id": str(rule.id),
                        "rule_name": rule.name,
                        "metric": rule.metric,
                        "threshold": rule.threshold,
                        "operator": rule.operator,
                        "value": value,
                    }
                )
        return triggered
