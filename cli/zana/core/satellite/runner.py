"""Satellite background process entrypoint."""

from __future__ import annotations

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [satellite] %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    from zana.core.multiuser import UserRegistry, load_satellite_config
    from zana.core.zsm import load_env_file

    load_env_file()
    config = load_satellite_config()
    registry = UserRegistry()

    # Read host aeon info for greeting messages
    host_aeon = "ZANA"
    host_name = "Admin"
    try:
        from zana.tui.aeon_dna import AeonProfile

        profile = AeonProfile.load()
        if profile:
            host_aeon = profile.name
    except Exception:
        pass

    gateway_url: str | None = config.get("gateway_url")

    if config.get("telegram_token"):
        from zana.core.satellite.telegram_bot import TelegramBot

        bot = TelegramBot(
            token=config["telegram_token"],
            registry=registry,
            host_aeon_name=host_aeon,
            host_name=host_name,
            gateway_url=gateway_url,
        )
        logger.info("Starting Telegram satellite…")
        asyncio.run(bot.run_polling())
    elif config.get("discord_token"):
        from zana.core.satellite.discord_bot import DiscordBot

        bot = DiscordBot(  # type: ignore[assignment]
            token=config["discord_token"],
            registry=registry,
            host_aeon_name=host_aeon,
            gateway_url=gateway_url,
        )
        logger.info("Starting Discord satellite…")
        asyncio.run(bot.run_polling())
    else:
        logger.error(
            "No platform configured. Run: zana satellite configure telegram <token>"
        )


if __name__ == "__main__":
    run()
