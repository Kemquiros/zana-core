"""Telegram long-polling satellite bot."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ONBOARD_FILE = Path.home() / ".zana" / "pending_onboard.json"
_ONBOARD_TTL = 86400  # 24h


class TelegramBot:
    def __init__(
        self,
        token: str,
        registry: Any,
        host_aeon_name: str = "ZANA",
        host_name: str = "Admin",
        gateway_url: str | None = None,
    ) -> None:
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}"
        self._registry = registry
        self._host_aeon = host_aeon_name
        self._host_name = host_name
        self._gateway_url = gateway_url
        self._running = True

    async def run_polling(self) -> None:
        offset = 0
        logger.info("Telegram satellite polling started")
        while self._running:
            try:
                updates = await self._get_updates(offset)
                for update in updates:
                    await self._handle_update(update)
                    offset = update["update_id"] + 1
            except Exception as exc:
                logger.warning("Polling error: %s", exc)
            await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def _get_updates(self, offset: int) -> list[dict]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=35) as client:
                r = await client.get(
                    f"{self._base}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                data = r.json()
                return data.get("result", []) if data.get("ok") else []
        except Exception:
            return []

    async def _handle_update(self, update: dict) -> None:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        text: str = msg.get("text", "").strip()
        tg_user_id = str(msg["from"]["id"])
        tg_username = msg["from"].get("first_name", "User")

        # Check pending onboarding state
        onboard_state = self._get_onboard_state(tg_user_id)
        if onboard_state:
            await self._handle_onboard_step(
                chat_id, tg_user_id, tg_username, text, onboard_state
            )
            return

        # /start with invite code
        if text.startswith("/start"):
            parts = text.split(" ", 1)
            code = parts[1].strip() if len(parts) > 1 else ""
            if code and self._registry.validate_invite(code):
                self._registry.consume_invite(code)
                await self._start_onboarding(chat_id, tg_user_id, tg_username)
                return
            elif not self._registry.get("telegram", tg_user_id):
                await self._send(chat_id, self._t("satellite.user.unknown"))
                return

        user = self._registry.get("telegram", tg_user_id)
        if not user:
            await self._send(chat_id, self._t("satellite.user.unknown"))
            return

        self._registry.touch("telegram", tg_user_id)
        lang = user.language

        response = await self._query_gateway(text, user) if self._gateway_url else None
        if not response:
            response = self._zsm_respond(text, user, lang)

        await self._send(chat_id, response)

    async def _start_onboarding(
        self, chat_id: int, tg_user_id: str, tg_username: str
    ) -> None:
        self._set_onboard_state(
            tg_user_id,
            {"step": "awaiting_name", "username": tg_username, "chat_id": chat_id},
        )
        msg = self._t(
            "satellite.onboarding.hello",
            username=tg_username,
            host_aeon=self._host_aeon,
            host_name=self._host_name,
        )
        await self._send(chat_id, msg)
        await self._send(chat_id, self._t("satellite.onboarding.ask_name"))

    async def _handle_onboard_step(
        self, chat_id: int, tg_user_id: str, tg_username: str, text: str, state: dict
    ) -> None:
        step = state.get("step")
        if step == "awaiting_name":
            aeon_name = text.strip() or tg_username
            state["aeon_name"] = aeon_name
            state["step"] = "awaiting_lang"
            self._set_onboard_state(tg_user_id, state)
            await self._send(chat_id, self._t("satellite.onboarding.ask_lang"))
        elif step == "awaiting_lang":
            lang_map = {
                "es": "es",
                "en": "en",
                "pt": "pt",
                "fr": "fr",
                "it": "it",
                "de": "de",
            }
            lang = lang_map.get(text.strip().lower()[:2], "es")
            aeon_name = state.get("aeon_name", tg_username)
            self._registry.register("telegram", tg_user_id, aeon_name, lang=lang)
            self._clear_onboard_state(tg_user_id)
            await self._send(
                chat_id,
                self._t("satellite.onboarding.ready", aeon_name=aeon_name, lang=lang),
            )

    def _zsm_respond(self, text: str, user: Any, lang: str) -> str:
        try:
            from cli.core.zsm import ZSMEngine

            engine = ZSMEngine(lang=lang, archetype=user.archetype)
            return engine.respond_text(text)
        except Exception as exc:
            logger.warning("ZSM error: %s", exc)
            return "..."

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
                        "user_id": user.user_id,
                        "lang": user.language,
                    },
                )
                if r.status_code == 200:
                    return r.json().get("response")
        except Exception:
            pass
        return None

    async def _send(self, chat_id: int, text: str) -> None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{self._base}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
        except Exception as exc:
            logger.warning("Send error: %s", exc)

    def _t(self, key: str, lang: str = "es", **kwargs: Any) -> str:
        try:
            from cli.core.i18n import t

            return t(key, lang=lang, **kwargs)
        except Exception:
            return key

    def _get_onboard_state(self, user_id: str) -> dict | None:
        try:
            if not ONBOARD_FILE.exists():
                return None
            data = json.loads(ONBOARD_FILE.read_text())
            entry = data.get(f"telegram_{user_id}")
            if not entry:
                return None
            if time.time() > entry.get("expires", 0):
                data.pop(f"telegram_{user_id}", None)
                ONBOARD_FILE.write_text(json.dumps(data))
                return None
            return entry
        except Exception:
            return None

    def _set_onboard_state(self, user_id: str, state: dict) -> None:
        try:
            data = {}
            if ONBOARD_FILE.exists():
                data = json.loads(ONBOARD_FILE.read_text())
            state["expires"] = int(time.time()) + _ONBOARD_TTL
            data[f"telegram_{user_id}"] = state
            ONBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
            ONBOARD_FILE.write_text(json.dumps(data))
        except Exception:
            pass

    def _clear_onboard_state(self, user_id: str) -> None:
        try:
            if not ONBOARD_FILE.exists():
                return
            data = json.loads(ONBOARD_FILE.read_text())
            data.pop(f"telegram_{user_id}", None)
            ONBOARD_FILE.write_text(json.dumps(data))
        except Exception:
            pass
