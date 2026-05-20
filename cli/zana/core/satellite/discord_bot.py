"""Discord Gateway satellite bot.

Uses Discord Gateway WebSocket (opcode-based) + REST API via httpx.
No discord.py required — only stdlib + httpx + websockets (both existing deps).

Intent flags:
  GUILDS               (1 << 0)
  GUILD_MESSAGES       (1 << 9)   — privileged; enable in Developer Portal
  MESSAGE_CONTENT      (1 << 15)  — privileged; enable in Developer Portal
  DIRECT_MESSAGES      (1 << 12)

Activation: zana satellite configure discord <BOT_TOKEN>
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
_API_BASE = "https://discord.com/api/v10"

# Privileged intents: GUILDS | GUILD_MESSAGES | MESSAGE_CONTENT | DIRECT_MESSAGES
_INTENTS = (1 << 0) | (1 << 9) | (1 << 12) | (1 << 15)

# Discord opcodes
_OP_DISPATCH = 0
_OP_HEARTBEAT = 1
_OP_IDENTIFY = 2
_OP_RECONNECT = 7
_OP_INVALID_SESSION = 9
_OP_HELLO = 10
_OP_HEARTBEAT_ACK = 11

COMMAND_PREFIX = "/zana"


class DiscordBot:
    """Discord Gateway bot for the ZANA satellite layer."""

    def __init__(
        self,
        token: str,
        registry: Any,
        host_aeon_name: str = "ZANA",
        host_name: str = "Admin",
        gateway_url: str | None = None,
    ) -> None:
        self._token = token
        self._registry = registry
        self._host_aeon = host_aeon_name
        self._host_name = host_name
        self._zana_gateway_url = gateway_url
        self._running = True
        self._sequence: int | None = None
        self._heartbeat_interval: float = 41.25
        self._bot_user_id: str | None = None
        self._stop_event = asyncio.Event()

    async def run_polling(self) -> None:
        logger.info("Discord satellite starting")
        while self._running:
            try:
                await self._connect()
            except Exception as exc:
                logger.warning("Discord gateway error: %s — reconnecting in 5s", exc)
                if self._running:
                    await asyncio.sleep(5)

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Gateway connection
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        import websockets

        async with websockets.connect(_GATEWAY_URL) as ws:
            self._ws = ws
            hello = json.loads(await ws.recv())
            self._heartbeat_interval = hello["d"]["heartbeat_jitter"] = (
                hello["d"]["heartbeat_interval"] / 1000
            )

            asyncio.ensure_future(self._heartbeat_loop(ws))
            await self._identify(ws)

            async for raw in ws:
                if not self._running:
                    break
                payload = json.loads(raw)
                await self._handle_payload(ws, payload)

    async def _identify(self, ws: Any) -> None:
        await ws.send(
            json.dumps(
                {
                    "op": _OP_IDENTIFY,
                    "d": {
                        "token": self._token,
                        "intents": _INTENTS,
                        "properties": {
                            "os": "linux",
                            "browser": "zana-satellite",
                            "device": "zana-satellite",
                        },
                    },
                }
            )
        )

    async def _heartbeat_loop(self, ws: Any) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await ws.send(json.dumps({"op": _OP_HEARTBEAT, "d": self._sequence}))
            except Exception:
                break

    # ------------------------------------------------------------------
    # Payload dispatch
    # ------------------------------------------------------------------

    async def _handle_payload(self, ws: Any, payload: dict) -> None:
        op = payload.get("op")
        if payload.get("s"):
            self._sequence = payload["s"]

        if op == _OP_DISPATCH:
            event = payload.get("t")
            data = payload.get("d", {})
            if event == "READY":
                self._bot_user_id = data.get("user", {}).get("id")
                logger.info("Discord READY — bot user ID: %s", self._bot_user_id)
            elif event == "MESSAGE_CREATE":
                await self._handle_message(data)
        elif op == _OP_RECONNECT:
            raise RuntimeError("Discord requested reconnect")
        elif op == _OP_INVALID_SESSION:
            raise RuntimeError("Discord invalid session")

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, data: dict) -> None:
        author = data.get("author", {})
        if author.get("bot"):
            return

        channel_id: str = data.get("channel_id", "")
        discord_user_id: str = author.get("id", "")
        username: str = author.get("username", "User")
        content: str = data.get("content", "").strip()
        guild_id: str | None = data.get("guild_id")

        # Accept: DMs to bot, or messages starting with /zana in guild channels
        is_dm = guild_id is None
        is_command = content.lower().startswith(COMMAND_PREFIX)

        if (
            not is_dm
            and not is_command
            and self._bot_user_id
            and f"<@{self._bot_user_id}>" not in content
        ):
            return

        # Strip prefix or mention
        prompt = content
        if is_command:
            prompt = content[len(COMMAND_PREFIX) :].strip()
        elif self._bot_user_id:
            prompt = content.replace(f"<@{self._bot_user_id}>", "").strip()

        user = self._registry.get("discord", discord_user_id)
        if not user:
            # Auto-register on first contact
            self._registry.register("discord", discord_user_id, username, lang="en")
            user = self._registry.get("discord", discord_user_id)

        self._registry.touch("discord", discord_user_id)
        lang = user.language if user else "en"

        response = (
            await self._query_gateway(prompt, user) if self._zana_gateway_url else None
        )
        if not response:
            response = self._zsm_respond(prompt, user, lang)

        await self._send_message(channel_id, response)

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
        if not self._zana_gateway_url:
            return None
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self._zana_gateway_url}/chat",
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

    async def _send_message(self, channel_id: str, content: str) -> None:
        import httpx

        # Discord message limit: 2000 chars
        if len(content) > 2000:
            content = content[:1997] + "..."
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{_API_BASE}/channels/{channel_id}/messages",
                    headers={"Authorization": f"Bot {self._token}"},
                    json={"content": content},
                )
        except Exception as exc:
            logger.warning("Discord send error: %s", exc)

    # ------------------------------------------------------------------
    # Token validation (called from satellite configure)
    # ------------------------------------------------------------------

    @staticmethod
    async def validate_token(token: str) -> bool:
        """Return True if the token authenticates successfully."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"{_API_BASE}/users/@me",
                    headers={"Authorization": f"Bot {token}"},
                )
                return r.status_code == 200
        except Exception:
            return False


def validate_discord_token_sync(token: str) -> bool:
    """Synchronous wrapper for token validation used in CLI configure command."""
    try:
        return asyncio.run(DiscordBot.validate_token(token))
    except Exception:
        return False
