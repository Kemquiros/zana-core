"""
ZANA Telegram Bot — entry point.

Run:
  python -m telegram_bot.bot

Required env vars:
  TELEGRAM_BOT_TOKEN          — from @BotFather
  ZANA_GATEWAY_URL            — e.g. http://localhost:54446 or https://api.zana.ai
  ZANA_TELEGRAM_ALLOWED_USERS — comma-separated Telegram user IDs (leave empty = public)

Optional:
  TELEGRAM_WEBHOOK_URL        — HTTPS URL for webhook mode (prod)
  TELEGRAM_WEBHOOK_PORT       — default 8443
  TELEGRAM_WEBHOOK_SECRET     — random secret token for webhook validation

Modes:
  - If TELEGRAM_WEBHOOK_URL is set → webhook mode (production, requires HTTPS)
  - Otherwise → long-polling mode  (development, no HTTPS needed)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

# Load .env from project root (walk up)
for _p in [Path(__file__).parent, *Path(__file__).parents]:
    if (_p / ".env").exists():
        load_dotenv(_p / ".env")
        break

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("zana.telegram.bot")

BOT_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL     = os.getenv("TELEGRAM_WEBHOOK_URL", "")
WEBHOOK_PORT    = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))
WEBHOOK_SECRET  = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
GATEWAY_URL     = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")


def _validate_env() -> None:
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set.\n"
            "Get one from @BotFather and add it to your .env:\n"
            "  TELEGRAM_BOT_TOKEN=<token>"
        )
        sys.exit(1)
    logger.info("✓  Gateway → %s", GATEWAY_URL)
    logger.info("✓  Mode    → %s", "webhook" if WEBHOOK_URL else "polling")


async def _post_init(app: Application) -> None:
    """Set bot commands visible in the Telegram menu."""
    commands = [
        BotCommand("start",   "Iniciar ZANA"),
        BotCommand("help",    "Lista de comandos"),
        BotCommand("status",  "Salud del sistema y ZFI"),
        BotCommand("recall",  "Últimos N recuerdos episódicos"),
        BotCommand("reason",  "Razonamiento simbólico: /reason fact=value"),
        BotCommand("swarm",   "Estado del enjambre Red Queen"),
        BotCommand("aeon",    "Flota de Aeons disponibles"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✓  Bot commands registered")


def build_app() -> Application:
    from telegram_bot.handlers import (
        cmd_start, cmd_help, cmd_status,
        cmd_recall, cmd_reason, cmd_swarm, cmd_aeon,
        handle_text, handle_voice, handle_photo, handle_callback,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("recall",  cmd_recall))
    app.add_handler(CommandHandler("reason",  cmd_reason))
    app.add_handler(CommandHandler("swarm",   cmd_swarm))
    app.add_handler(CommandHandler("aeon",    cmd_aeon))

    # Inline callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Messages
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO,                  handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


def main() -> None:
    _validate_env()
    app = build_app()

    print("╔══════════════════════════════════════════════════╗")
    print("║   ZANA TELEGRAM BOT  v2.0                        ║")
    print(f"║   Gateway → {GATEWAY_URL:<36}║")
    print(f"║   Mode    → {'webhook' if WEBHOOK_URL else 'polling':<36}║")
    print("╚══════════════════════════════════════════════════╝")

    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=WEBHOOK_PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=["message", "callback_query"],
        )
    else:
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
