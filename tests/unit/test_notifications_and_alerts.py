"""Notification delivery and alert evaluation edge cases."""

import json
from datetime import datetime, timedelta, timezone

import httpx

from src.database.models.sqlalchemy_models import AlertRule
from src.services import notification_service
from src.services.alert_service import AlertService
from src.services.notification_service import NotificationService


def patch_httpx(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(notification_service.httpx, "AsyncClient", factory)


async def test_webhook_payload(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200)

    patch_httpx(monkeypatch, handler)
    ok = await NotificationService().send("https://hooks.example/x", "msg", {"a": 1})
    assert ok is True
    assert seen[0].url == "https://hooks.example/x"
    assert json.loads(seen[0].read()) == {"text": "msg", "payload": {"a": 1}}


async def test_webhook_http_error_returns_false(monkeypatch):
    patch_httpx(monkeypatch, lambda request: httpx.Response(500))
    assert await NotificationService().send("https://hooks.example/x", "m", {}) is False


async def test_log_channel_and_unsupported():
    assert await NotificationService().send(None, "m", {}) is True
    assert await NotificationService().send("log", "m", {}) is True
    assert await NotificationService().send("smtp://x", "m", {}) is False


class FailingNotifier(NotificationService):
    async def send(self, channel, message, payload):
        return False


async def test_failed_delivery_does_not_start_cooldown(db_session):
    rule = AlertRule(name="r", metric="total_traces", threshold=0, operator=">=", window_minutes=5)
    db_session.add(rule)
    await db_session.commit()

    results = await AlertService(db_session, notifier=FailingNotifier()).evaluate_all()
    assert results[0]["breached"] is True
    assert results[0]["notified"] is False
    await db_session.refresh(rule)
    assert rule.last_triggered_at is None


async def test_cooldown_expires(db_session):
    now = datetime.now(timezone.utc)
    rule = AlertRule(
        name="r", metric="total_traces", threshold=0, operator=">=", window_minutes=5,
        last_triggered_at=now - timedelta(hours=1),
    )
    disabled = AlertRule(name="off", metric="total_traces", threshold=0, operator=">=",
                         enabled=False)
    db_session.add_all([rule, disabled])
    await db_session.commit()

    results = await AlertService(db_session).evaluate_all(now=now)
    assert [r["rule_name"] for r in results] == ["r"]
    assert results[0]["notified"] is True
