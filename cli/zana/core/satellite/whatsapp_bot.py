"""WhatsApp Cloud API satellite bot.

Uses WhatsApp Business Cloud API (Meta Graph API v18.0) via httpx.
No third-party WhatsApp library — only stdlib + httpx (existing dep).

Setup:
  1. Create a Meta App → WhatsApp Business → add a test phone number
  2. Generate a permanent system-user access token
  3. Register your webhook URL in the Meta Developer Portal
  4. zana satellite configure whatsapp <access_token> --phone-number-id <phone_number_id>

Webhook verification:
  Meta sends a GET ?hub.mode=subscribe&hub.challenge=...&hub.verify_token=...
  The bot responds with hub.challenge when hub.verify_token matches VERIFY_TOKEN.
  Set ZANA_WA_VERIFY_TOKEN in ~/.zana/.env (or the config) before registering.

Message routing:
  - Only text messages are processed; reactions/media are silently ignored
  - All inbound messages trigger a ZSM response
  - Replies are sent to the sender's phone number
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_API_BASE = "https://graph.facebook.com/v18.0"
_MESSAGE_LIMIT = 4096  # WhatsApp text message cap


class WhatsAppBot:
    """WhatsApp Cloud API bot for the ZANA satellite layer."""

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        registry: Any,
        host_aeon_name: str = "ZANA",
        gateway_url: str | None = None,
        verify_token: str = "zana_wa_verify",
    ) -> None:
        self._phone_number_id = phone_number_id
        self._token = access_token
        self._registry = registry
        self._host_aeon = host_aeon_name
        self._gateway_url = gateway_url
        self._verify_token = verify_token

    # ------------------------------------------------------------------
    # Webhook payload handling (called from HTTP server)
    # ------------------------------------------------------------------

    async def handle_webhook(self, payload: dict) -> None:
        """Dispatch inbound webhook payload from Meta."""
        entry = payload.get("entry", [])
        for e in entry:
            for change in e.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    await self._handle_message(msg)

    async def _handle_message(self, msg: dict) -> None:
        if msg.get("type") != "text":
            return

        wa_id: str = msg.get("from", "")
        text: str = msg.get("text", {}).get("body", "").strip()
        if not text:
            return

        user = self._registry.get("whatsapp", wa_id)
        if not user:
            self._registry.register("whatsapp", wa_id, wa_id, lang="en")
            user = self._registry.get("whatsapp", wa_id)
        else:
            self._registry.touch("whatsapp", wa_id)
        lang = user.language if user else "en"

        response = await self._query_gateway(text, user) if self._gateway_url else None
        if not response:
            response = self._zsm_respond(text, user, lang)

        await self.send_message(wa_id, response)

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------

    async def send_message(self, to: str, content: str) -> None:
        """Send a text message to a WhatsApp number."""
        import httpx

        if len(content) > _MESSAGE_LIMIT:
            content = content[: _MESSAGE_LIMIT - 3] + "..."

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": content},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{_API_BASE}/{self._phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=payload,
                )
                if resp.status_code not in (200, 201):
                    logger.warning(
                        "WhatsApp API returned %d for %s: %s",
                        resp.status_code,
                        to,
                        resp.text[:200],
                    )
        except Exception as exc:
            logger.warning("WhatsApp send error: %s", exc)

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def _zsm_respond(self, text: str, user: Any, lang: str) -> str:
        try:
            from zana.core.zsm import ZSMEngine

            engine = ZSMEngine(
                lang=lang, archetype=getattr(user, "archetype", "unknown")
            )
            return engine.respond_text(text)
        except Exception as exc:
            logger.warning("ZSM error: %s", exc)
            return "I'm processing your request — try again in a moment."

    async def _query_gateway(self, text: str, user: Any) -> str | None:
        if not self._gateway_url:
            return None
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self._gateway_url}/chat",
                    json={
                        "message": text,
                        "user_id": getattr(user, "user_id", ""),
                        "lang": getattr(user, "language", "en"),
                    },
                )
                if r.status_code == 200:
                    return r.json().get("response")
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def verify_webhook(
        self, mode: str, challenge: str, verify_token: str
    ) -> str | None:
        """Return hub.challenge if verification passes, else None."""
        if mode == "subscribe" and verify_token == self._verify_token:
            return challenge
        return None

    # ------------------------------------------------------------------
    # Token validation (called from satellite configure)
    # ------------------------------------------------------------------

    @staticmethod
    async def validate_token(access_token: str) -> bool:
        """Return True if the access_token authenticates against Graph API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"{_API_BASE}/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return r.status_code == 200 and "id" in r.json()
        except Exception:
            return False


def validate_whatsapp_token_sync(access_token: str) -> bool:
    """Synchronous wrapper for token validation used in CLI configure command."""
    import asyncio

    try:
        return asyncio.run(WhatsAppBot.validate_token(access_token))
    except Exception:
        return False
