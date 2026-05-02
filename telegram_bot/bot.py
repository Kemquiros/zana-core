"""
ZANA Telegram Bot — Herald Gateway v3.0.

Run:
  python -m telegram_bot.bot

Required env vars:
  TELEGRAM_BOT_TOKEN              — from @BotFather
  ZANA_GATEWAY_URL                — default: http://localhost:54446
  ZANA_TELEGRAM_ALLOWED_USERS     — comma-separated Telegram user IDs (empty = public)

Optional:
  TELEGRAM_WEBHOOK_URL            — HTTPS URL for webhook mode (production)
  TELEGRAM_WEBHOOK_PORT           — default 8443
  TELEGRAM_WEBHOOK_SECRET         — random secret for webhook validation
  ZANA_TG_HEALTH_INTERVAL         — seconds between health checks (default 60)
  ZANA_TG_RATE_LIMIT              — messages/minute per user (default 10)
  ZANA_TG_NOTIFY_ADMIN            — Telegram user_id to notify on gateway down/up

Modes:
  TELEGRAM_WEBHOOK_URL set → webhook mode (production, HTTPS required)
  Otherwise               → long-polling mode (development)

Robustness features (v3.0):
  - Circuit breaker in gateway_client (5 failures → 30s cooldown)
  - Retry with exponential backoff (3 attempts per request)
  - Per-user rate limiting (token bucket, default 10 msg/min)
  - Background health monitor: pings gateway every 60s, alerts admin on state change
  - Document handler: .txt .md .py .json .csv up to 1 MB
  - Inline keyboards for wisdom approve/reject (no manual ID copy-paste)
  - /clear command to reset session context
  - Typed error messages (GatewayDown vs Timeout vs Rejected)
"""

from __future__ import annotations

import asyncio
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

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL  = os.getenv("TELEGRAM_WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
GATEWAY_URL  = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
HEALTH_INTERVAL = int(os.getenv("ZANA_TG_HEALTH_INTERVAL", "60"))
NOTIFY_ADMIN = os.getenv("ZANA_TG_NOTIFY_ADMIN", "")

VERSION = "3.0.0"


def _validate_env() -> None:
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set.\n"
            "Get one from @BotFather and add to .env:\n"
            "  TELEGRAM_BOT_TOKEN=<token>"
        )
        sys.exit(1)
    logger.info("✓  Gateway  → %s", GATEWAY_URL)
    logger.info("✓  Mode     → %s", "webhook" if WEBHOOK_URL else "polling")
    logger.info("✓  Version  → %s", VERSION)


async def _post_init(app: Application) -> None:
    """Set bot commands and start background health monitor."""
    commands = [
        BotCommand("start",  "Iniciar ZANA"),
        BotCommand("help",   "Lista de comandos"),
        BotCommand("status", "Salud del sistema, ZFI y Sentinel"),
        BotCommand("recall", "Últimos N recuerdos episódicos"),
        BotCommand("reason", "Razonamiento simbólico: /reason fact=value"),
        BotCommand("swarm",  "Estado del enjambre Red Queen"),
        BotCommand("aeon",   "Flota de Aeons disponibles"),
        BotCommand("wisdom", "Wisdom inbox: /wisdom [mine|approve|reject]"),
        BotCommand("clear",  "Limpiar contexto de sesión"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✓  Bot commands registered (%d)", len(commands))

    # Start health monitor
    asyncio.create_task(_health_monitor(app))


# ── Background health monitor ─────────────────────────────────────────────────

async def _health_monitor(app: Application) -> None:
    """
    Pings the ZANA gateway every HEALTH_INTERVAL seconds.
    Sends a Telegram notification to NOTIFY_ADMIN when gateway goes down or recovers.
    Logs a warning every cycle when down (visible in docker logs).
    """
    from telegram_bot import gateway_client as gw
    from telegram_bot.gateway_client import GatewayDown, GatewayTimeout

    gateway_was_up: bool | None = None

    async def _notify(text: str) -> None:
        if NOTIFY_ADMIN:
            try:
                await app.bot.send_message(chat_id=NOTIFY_ADMIN, text=text)
            except Exception as e:
                logger.warning("Admin notify failed: %s", e)

    while True:
        await asyncio.sleep(HEALTH_INTERVAL)
        try:
            await gw.health()
            if gateway_was_up is False:
                logger.info("Gateway recovered ✓")
                await _notify("✅ *ZANA gateway recuperado.* El Aeon está en línea.")
            gateway_was_up = True
        except (GatewayDown, GatewayTimeout, Exception) as e:
            if gateway_was_up is not False:
                logger.warning("Gateway unreachable: %s", e)
                await _notify(
                    f"⚠️ *ZANA gateway caído.*\n`{GATEWAY_URL}`\n"
                    f"Error: `{str(e)[:100]}`\n\n"
                    f"Ejecuta `zana status` y `zana start` en el servidor."
                )
            gateway_was_up = False


# ── App builder ───────────────────────────────────────────────────────────────

def build_app() -> Application:
    from telegram_bot.handlers import (
        cmd_start, cmd_help, cmd_clear, cmd_status,
        cmd_recall, cmd_reason, cmd_swarm, cmd_aeon, cmd_wisdom,
        handle_text, handle_voice, handle_photo, handle_document, handle_callback,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .concurrent_updates(True)   # handle multiple users simultaneously
        .build()
    )

    # ── Commands ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("recall", cmd_recall))
    app.add_handler(CommandHandler("reason", cmd_reason))
    app.add_handler(CommandHandler("swarm",  cmd_swarm))
    app.add_handler(CommandHandler("aeon",   cmd_aeon))
    app.add_handler(CommandHandler("wisdom", cmd_wisdom))

    # ── Inline callbacks ──────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── Messages ──────────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


def main() -> None:
    _validate_env()
    app = build_app()

    print("╔══════════════════════════════════════════════════╗")
    print(f"║   ZANA HERALD GATEWAY  v{VERSION:<24}║")
    print(f"║   Gateway  → {GATEWAY_URL:<36}║")
    print(f"║   Mode     → {'webhook' if WEBHOOK_URL else 'polling':<36}║")
    print(f"║   Health ↻ every {HEALTH_INTERVAL}s{'':<29}║")
    print("╚══════════════════════════════════════════════════╝")

    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=WEBHOOK_PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
    else:
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
