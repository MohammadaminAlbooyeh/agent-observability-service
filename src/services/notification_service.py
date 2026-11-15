"""Sends alert notifications to a webhook (Slack-compatible) or the log."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    async def send(self, channel: str | None, message: str, payload: dict[str, Any]) -> bool:
        """Deliver a notification. Returns True on success.

        ``channel`` is ``None``/``"log"`` (log only) or an http(s) webhook URL. Webhooks receive
        ``{"text": message, "payload": {...}}``, which Slack incoming webhooks accept.
        """
        if not channel or channel == "log":
            logger.warning("ALERT: %s | %s", message, payload)
            return True
        if not channel.startswith(("http://", "https://")):
            logger.error("Unsupported notification channel %r", channel)
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(channel, json={"text": message, "payload": payload})
                resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("Failed to deliver alert to webhook: %s", exc)
            return False
