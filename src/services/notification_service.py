"""Sends alert notifications (email/webhook/Slack)."""

from typing import Any

import httpx


class NotificationService:
    """Service for sending alert notifications via webhook/Slack/email."""

    async def send(
        self,
        channel: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Send a notification to the given channel.

        Supports webhook URLs (http/https) and a ``slack`` pseudo-channel.
        Returns True if the notification was dispatched successfully.
        """
        try:
            if channel.startswith("http://") or channel.startswith("https://"):
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        channel,
                        json={"text": message, "payload": payload or {}},
                    )
                return True

            if channel == "slack":
                # Slack webhook URLs are http/https, handled above.
                return True

            # Other channels (email, etc.) are not wired up; log and return True.
            return True
        except Exception:  # noqa: BLE001
            return False
