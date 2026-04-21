"""
ZANA Slack Bot — listens to Slack events and routes them to the Gateway.

Uses Slack Bolt with Socket Mode (no public URL needed for development).
For production, set SLACK_WEBHOOK_PATH and use an HTTP server.

Required env vars:
  SLACK_BOT_TOKEN      — xoxb-... (Bot User OAuth Token)
  SLACK_APP_TOKEN      — xapp-... (App-Level Token, for Socket Mode)
  ZANA_GATEWAY_URL     — http://localhost:54446
  ZANA_SLACK_BOT_USER  — bot's own Slack user ID (to avoid self-replies)

Commands (via slash or mention):
  /zana <text>          → /sense/text → response posted to channel
  /zana reason <fact>   → /reason → deductions posted
  /zana recall [n]      → /memory/episodic → memories posted
  /zana status          → /health → status posted
  @ZANA <text>          → same as /zana <text>
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("zana.slack.bot")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
GATEWAY_URL     = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
BOT_USER_ID     = os.getenv("ZANA_SLACK_BOT_USER", "")

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

app = App(token=SLACK_BOT_TOKEN)


def _gw_sense(text: str, channel: str) -> str:
    try:
        r = httpx.post(f"{GATEWAY_URL}/sense/text",
                       json={"text": text, "session_id": f"slack-{channel}"},
                       timeout=_TIMEOUT)
        data = r.json()
        return data.get("response_text") or data.get("text") or "…"
    except Exception as e:
        return f"⚠️ Gateway error: {e}"


def _gw_reason(fact_raw: str) -> str:
    k, _, v = fact_raw.partition("=")
    try:
        val: float | str = float(v)
    except ValueError:
        val = v
    try:
        r = httpx.post(f"{GATEWAY_URL}/reason",
                       json={"fact": {"fact_key": k.strip(), "value": val}},
                       timeout=_TIMEOUT)
        result = r.json()
        deductions = result.get("deductions", [])
        if not deductions:
            return f"No deductions for `{fact_raw}`."
        lines = [f"🧠 *Reasoning: {fact_raw}*\n"]
        for d in deductions:
            lines.append(f"• *{d['rule']}* ({d.get('confidence', 0):.0%}) → {d['conclusion']}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Reason error: {e}"


def _gw_health() -> str:
    try:
        r = httpx.get(f"{GATEWAY_URL}/health", timeout=httpx.Timeout(5.0))
        d = r.json()
        backends = d.get("backends", {})
        icon = {"stt": "🎤", "tts": "🔊", "llm": "🧠", "vision": "👁️", "kalman": "📐", "armor": "🛡️"}
        lines = ["⚙️ *ZANA — Online*\n"]
        lines += [f"{icon.get(k, '·')} `{k}`: {v}" for k, v in backends.items()]
        return "\n".join(lines)
    except Exception:
        return "⚠️ Gateway offline."


# ── /zana slash command ───────────────────────────────────────────────────────

@app.command("/zana")
def handle_zana_command(ack, respond, command):
    ack()
    text = (command.get("text") or "").strip()
    channel = command.get("channel_id", "")

    if not text or text == "help":
        respond(
            "*ZANA Commands:*\n"
            "`/zana <text>` — converse with ZANA\n"
            "`/zana reason fact=value` — symbolic reasoning\n"
            "`/zana recall [n]` — last N memories\n"
            "`/zana status` — system health\n"
        )
        return

    if text.startswith("reason "):
        respond(_gw_reason(text[7:].strip()))
    elif text.startswith("recall"):
        parts = text.split()
        n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
        try:
            records = httpx.get(f"{GATEWAY_URL}/memory/episodic?limit={n}",
                                timeout=_TIMEOUT).json()
            if not records:
                respond("No episodic records yet.")
            else:
                lines = [f"📚 *Last {len(records)} memories:*\n"]
                for rec in records:
                    ts = (rec.get("created_at") or "")[:16]
                    role = "user" if rec.get("role") == "user" else "ZANA"
                    lines.append(f"[{ts}] *{role}:* {(rec.get('content') or '')[:120]}")
                respond("\n".join(lines))
        except Exception as e:
            respond(f"⚠️ {e}")
    elif text == "status":
        respond(_gw_health())
    else:
        respond(f"🧠 *ZANA:* {_gw_sense(text, channel)}")


# ── @mention handler ──────────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, say):
    text = event.get("text", "")
    channel = event.get("channel", "")
    user = event.get("user", "")

    # Strip bot mention (<@UXXXXXXX> ...)
    if BOT_USER_ID:
        text = text.replace(f"<@{BOT_USER_ID}>", "").strip()
    else:
        # Fallback: remove first <@...> token
        import re
        text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not text:
        say("Hola. ¿Qué necesitas? Usa `/zana help` para ver los comandos.")
        return

    response = _gw_sense(text, channel)
    say(f"<@{user}> 🧠 {response}")


# ── Direct message handler ────────────────────────────────────────────────────

@app.event("message")
def handle_dm(event, say, client):
    # Only respond to DMs (channel type = 'im'), not channel messages
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):  # ignore bot messages
        return

    text = event.get("text", "").strip()
    channel = event.get("channel", "")
    if not text:
        return

    response = _gw_sense(text, channel)
    say(f"🧠 {response}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not set. Get one from api.slack.com/apps")
        return
    if not SLACK_APP_TOKEN:
        logger.error("SLACK_APP_TOKEN not set. Enable Socket Mode in your Slack app settings.")
        return

    logger.info("🔌 ZANA Slack Bot starting (Socket Mode)…")
    logger.info("   Gateway → %s", GATEWAY_URL)

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
