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
    elif config.get("whatsapp_token"):
        import signal

        from zana.core.satellite.whatsapp_bot import WhatsAppBot

        phone_number_id = config.get("whatsapp_phone_number_id", "")
        verify_token = config.get("whatsapp_verify_token", "zana_wa_verify")
        bot = WhatsAppBot(  # type: ignore[assignment]
            phone_number_id=phone_number_id,
            access_token=config["whatsapp_token"],
            registry=registry,
            host_aeon_name=host_aeon,
            gateway_url=gateway_url,
            verify_token=verify_token,
        )
        logger.info("WhatsApp satellite configured (webhook mode — no polling loop).")
        logger.info(
            "Register your webhook URL in the Meta Developer Portal "
            "then route POST /webhook payloads to bot.handle_webhook()."
        )

        async def _wait_for_signal() -> None:
            loop = asyncio.get_running_loop()
            stop: asyncio.Future[None] = loop.create_future()
            loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
            loop.add_signal_handler(signal.SIGINT, stop.set_result, None)
            await stop

        asyncio.run(_wait_for_signal())
    else:
        logger.error(
            "No platform configured. Run: zana satellite configure telegram <token>"
        )


if __name__ == "__main__":
    run()
