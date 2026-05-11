"""Discord gateway satellite bot (minimal stub — expandable)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DiscordBot:
    """Discord bot via gateway WebSocket. Requires 'discord.py' or 'hikari' installed."""

    def __init__(
        self,
        token: str,
        registry: Any,
        host_aeon_name: str = "ZANA",
        gateway_url: str | None = None,
    ) -> None:
        self._token = token
        self._registry = registry
        self._host_aeon = host_aeon_name
        self._gateway_url = gateway_url
        self._running = True

    async def run_polling(self) -> None:
        logger.info("Discord satellite polling started (stub)")
        self._stop_event = asyncio.Event()
        # Full implementation requires discord.py or hikari.
        # This stub waits on an event — wire real gateway events here.
        await self._stop_event.wait()

    def stop(self) -> None:
        self._running = False
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
