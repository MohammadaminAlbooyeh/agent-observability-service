"""Alert rule CRUD and evaluation against current metrics."""

import logging
import operator as op
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.alert import AlertRuleCreate, AlertRuleUpdate
from src.config.settings import settings
from src.database.models.sqlalchemy_models import AlertRule
from src.services.metrics_service import MetricFilter, MetricsService
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

OPERATORS = {">": op.gt, "<": op.lt, ">=": op.ge, "<=": op.le, "==": op.eq}


def serialize_rule(rule: AlertRule) -> dict[str, Any]:
    last = rule.last_triggered_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return {
        "id": rule.id,
        "name": rule.name,
        "metric": rule.metric,
        "threshold": rule.threshold,
        "operator": rule.operator,
        "window_minutes": rule.window_minutes,
        "channel": rule.channel,
        "project_id": rule.project_id,
        "enabled": rule.enabled,
        "last_triggered_at": last.isoformat() if last else None,
    }


class AlertService:
    def __init__(self, session: AsyncSession, notifier: NotificationService | None = None):
        self.session = session
        self.notifier = notifier or NotificationService()

    async def create_rule(self, rule: AlertRuleCreate) -> dict[str, Any]:
        db_rule = AlertRule(**rule.model_dump())
        self.session.add(db_rule)
        await self.session.commit()
        return serialize_rule(db_rule)

    async def list_rules(self, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        stmt = select(AlertRule).order_by(AlertRule.created_at)
        if project_id:
            stmt = stmt.where(AlertRule.project_id == project_id)
        return [serialize_rule(r) for r in (await self.session.execute(stmt)).scalars()]

    async def get_rule(self, rule_id: str) -> Optional[dict[str, Any]]:
        rule = await self.session.get(AlertRule, rule_id)
        return serialize_rule(rule) if rule else None

    async def update_rule(self, rule_id: str, update: AlertRuleUpdate) -> Optional[dict]:
        rule = await self.session.get(AlertRule, rule_id)
        if rule is None:
            return None
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        await self.session.commit()
        return serialize_rule(rule)

    async def delete_rule(self, rule_id: str) -> bool:
        rule = await self.session.get(AlertRule, rule_id)
        if rule is None:
            return False
        await self.session.delete(rule)
        await self.session.commit()
        return True

    async def evaluate_all(self, now: Optional[datetime] = None) -> list[dict[str, Any]]:
        """Evaluate every enabled rule; notify on breaches outside the cooldown window."""
        now = now or datetime.now(timezone.utc)
        cooldown = timedelta(seconds=settings.alert_cooldown_seconds)
        metrics = MetricsService(self.session)
        snapshots: dict[tuple[Optional[str], int], dict[str, Any]] = {}
        results = []

        rules = (
            await self.session.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
        ).scalars().all()
        for rule in rules:
            key = (rule.project_id, rule.window_minutes)
            if key not in snapshots:
                since = now - timedelta(minutes=rule.window_minutes)
                snapshots[key] = await metrics.snapshot(MetricFilter(rule.project_id, since))
            value = snapshots[key][rule.metric]
            breached = OPERATORS[rule.operator](value, rule.threshold)

            last = rule.last_triggered_at
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            in_cooldown = last is not None and now - last < cooldown

            notified = False
            if breached and not in_cooldown:
                message = (
                    f"[{rule.name}] {rule.metric}={value} {rule.operator} {rule.threshold} "
                    f"(last {rule.window_minutes}m)"
                )
                payload = {**serialize_rule(rule), "value": value}
                notified = await self.notifier.send(rule.channel, message, payload)
                if notified:
                    rule.last_triggered_at = now

            results.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "metric": rule.metric,
                    "operator": rule.operator,
                    "threshold": rule.threshold,
                    "value": value,
                    "breached": breached,
                    "notified": notified,
                    "in_cooldown": breached and in_cooldown,
                }
            )

        await self.session.commit()
        return results
