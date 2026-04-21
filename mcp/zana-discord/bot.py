"""
ZANA Discord Bot — listens to Discord events and routes them to the Gateway.

Uses discord.py with slash commands (app_commands) and on_message fallback.

Required env vars:
  DISCORD_BOT_TOKEN      — from discord.com/developers/applications
  DISCORD_GUILD_ID       — optional: guild ID for instant slash command sync
  ZANA_GATEWAY_URL       — http://localhost:54446
  ZANA_DISCORD_ALLOWED   — comma-separated Discord user IDs (empty = public)

Commands:
  /sense <text>         → full cognitive pipeline → response
  /reason <fact>        → forward-chaining → deduction trace
  /recall [n]           → last N episodic memories
  /status               → gateway health
  /swarm                → swarm fleet summary
  @ZANA <text>          → same as /sense
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import discord
from discord import app_commands
import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("zana.discord.bot")

DISCORD_BOT_TOKEN  = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID   = os.getenv("DISCORD_GUILD_ID", "")
GATEWAY_URL        = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
ALLOWED_USERS      = set(filter(None, os.getenv("ZANA_DISCORD_ALLOWED", "").split(",")))

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

intents = discord.Intents.default()
intents.message_content = True


class ZanaBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("✓ Slash commands synced to guild %s", DISCORD_GUILD_ID)
        else:
            await self.tree.sync()
            logger.info("✓ Slash commands synced globally (may take up to 1h)")


client = ZanaBot()


def _allowed(user_id: int) -> bool:
    return not ALLOWED_USERS or str(user_id) in ALLOWED_USERS


# ── Gateway helpers ───────────────────────────────────────────────────────────

async def _sense(text: str, session_id: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{GATEWAY_URL}/sense/text",
                             json={"text": text, "session_id": session_id})
            data = r.json()
            response = data.get("response_text") or data.get("text") or "…"
            surprise = data.get("kalman_surprise", 0)
            if surprise > 1.5:
                response += f"\n-# surprise: {surprise:.2f}"
            return response
    except Exception as e:
        return f"⚠️ Gateway error: {e}"


async def _reason(fact_raw: str) -> str:
    k, _, v = fact_raw.partition("=")
    try:
        val: float | str = float(v)
    except ValueError:
        val = v
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{GATEWAY_URL}/reason",
                             json={"fact": {"fact_key": k.strip(), "value": val}})
            result = r.json()
        deductions = result.get("deductions", [])
        if not deductions:
            return f"No deductions for `{fact_raw}`."
        lines = [f"🧠 **Reasoning: {fact_raw}**\n"]
        for d in deductions:
            lines.append(f"• **{d['rule']}** ({d.get('confidence', 0):.0%}) → {d['conclusion']}")
            if d.get("action"):
                lines.append(f"  ⚡ `{d['action']}`")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ {e}"


async def _recall(n: int) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{GATEWAY_URL}/memory/episodic", params={"limit": n})
            records = r.json()
        if not records:
            return "No episodic records yet."
        lines = [f"📚 **Last {len(records)} memories:**\n"]
        for rec in records:
            ts = (rec.get("created_at") or "")[:16]
            role = "user" if rec.get("role") == "user" else "ZANA"
            lines.append(f"`{ts}` **{role}:** {(rec.get('content') or '')[:120]}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ {e}"


async def _health() -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as c:
            r = await c.get(f"{GATEWAY_URL}/health")
            d = r.json()
        backends = d.get("backends", {})
        icon = {"stt": "🎤", "tts": "🔊", "llm": "🧠", "vision": "👁️", "kalman": "📐", "armor": "🛡️"}
        lines = ["⚙️ **ZANA Gateway — Online**\n"]
        lines += [f"{icon.get(k, '·')} `{k}`: {v}" for k, v in backends.items()]
        return "\n".join(lines)
    except Exception:
        return "⚠️ Gateway offline."


async def _swarm() -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as c:
            r = await c.get(f"{GATEWAY_URL}/swarm/status")
            d = r.json()
        s = d.get("summary", {})
        status = "🟢 Online" if d.get("running") else "⚫ Offline"
        return (
            f"🐝 **Red Queen — {status}**\n"
            f"Warriors: `{s.get('total', 0)}` | Active: `{s.get('active', 0)}` | "
            f"Legends: `{s.get('legends', 0)}` | Avg fitness: `{s.get('avg_fitness', 0):.3f}`\n"
            f"Generation: `{d.get('current_generation', 0)}`"
        )
    except Exception:
        return "⚠️ Swarm offline."


# ── Slash commands ────────────────────────────────────────────────────────────

@client.tree.command(name="sense", description="Send a message to ZANA's cognitive pipeline")
@app_commands.describe(text="What you want to say or ask ZANA")
async def slash_sense(interaction: discord.Interaction, text: str):
    if not _allowed(interaction.user.id):
        await interaction.response.send_message("⛔ Access denied.", ephemeral=True)
        return
    await interaction.response.defer()
    session_id = f"discord-{interaction.channel_id}"
    response = await _sense(text, session_id)
    await interaction.followup.send(f"🧠 **ZANA:** {response[:1900]}")


@client.tree.command(name="reason", description="Trigger symbolic reasoning with a structured fact")
@app_commands.describe(fact="Fact in key=value format (e.g. machine_health_avg=0.3)")
async def slash_reason(interaction: discord.Interaction, fact: str):
    if not _allowed(interaction.user.id):
        await interaction.response.send_message("⛔ Access denied.", ephemeral=True)
        return
    await interaction.response.defer()
    result = await _reason(fact)
    await interaction.followup.send(result[:1900])


@client.tree.command(name="recall", description="Retrieve last N episodic memories")
@app_commands.describe(n="Number of memories to show (1-20, default 5)")
async def slash_recall(interaction: discord.Interaction, n: int = 5):
    if not _allowed(interaction.user.id):
        await interaction.response.send_message("⛔ Access denied.", ephemeral=True)
        return
    await interaction.response.defer()
    result = await _recall(min(n, 20))
    await interaction.followup.send(result[:1900])


@client.tree.command(name="status", description="Show ZANA system health")
async def slash_status(interaction: discord.Interaction):
    await interaction.response.defer()
    result = await _health()
    await interaction.followup.send(result)


@client.tree.command(name="swarm", description="Show Red Queen swarm status")
async def slash_swarm(interaction: discord.Interaction):
    await interaction.response.defer()
    result = await _swarm()
    await interaction.followup.send(result)


# ── @mention + DM handler ────────────────────────────────────────────────────

@client.event
async def on_ready():
    logger.info("✓ ZANA Discord Bot ready — logged in as %s (ID: %s)",
                client.user.name, client.user.id)
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="the cognitive horizon")
    )


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if not _allowed(message.author.id):
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mention = client.user in message.mentions

    if not (is_dm or is_mention):
        return

    text = message.content
    if is_mention and client.user:
        text = text.replace(f"<@{client.user.id}>", "").strip()

    if not text:
        await message.reply("Hola. Usa `/sense <texto>` o mencioname con tu pregunta.")
        return

    async with message.channel.typing():
        session_id = f"discord-dm-{message.author.id}" if is_dm else f"discord-{message.channel.id}"
        response = await _sense(text, session_id)
        await message.reply(f"🧠 {response[:1900]}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not DISCORD_BOT_TOKEN:
        logger.error(
            "DISCORD_BOT_TOKEN not set.\n"
            "  1. Go to discord.com/developers/applications\n"
            "  2. Create an app → Bot → Reset Token\n"
            "  3. Add to .env: DISCORD_BOT_TOKEN=<token>"
        )
        return
    logger.info("🎮 ZANA Discord Bot starting…")
    logger.info("   Gateway → %s", GATEWAY_URL)
    client.run(DISCORD_BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
