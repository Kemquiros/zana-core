"""
ZANA MCP Server for Discord (zana-discord).

Exposes ZANA's cognitive capabilities as MCP tools consumable by any
MCP-compatible client (Claude Code, Claude Desktop, etc.).

Tools:
  discord_send      — post a message to any Discord channel
  discord_read      — read recent messages from a channel
  discord_sense     — route text to ZANA Gateway and optionally post response
  discord_reason    — trigger forward-chaining and post deductions
  discord_recall    — fetch episodic memories and post them
  discord_status    — post ZANA system health
  discord_channels  — list accessible text channels

Run as MCP server:
  uv run mcp dev server.py
  uv run python server.py     # stdio (Claude Desktop)

Required env vars:
  DISCORD_BOT_TOKEN   — from discord.com/developers/applications
  ZANA_GATEWAY_URL    — http://localhost:54446
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx
from mcp.server.fastmcp import FastMCP

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GATEWAY_URL       = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")

mcp = FastMCP("zana-discord")

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_DISCORD_API = "https://discord.com/api/v10"


# ── Discord REST helpers ──────────────────────────────────────────────────────

def _dh() -> dict:
    return {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}


def _d_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(f"{_DISCORD_API}{path}", json=payload, headers=_dh())
        return r.json()


def _d_get(path: str, params: dict | None = None) -> dict | list:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.get(f"{_DISCORD_API}{path}", params=params, headers=_dh())
        return r.json()


def _gw_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(f"{GATEWAY_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


def _gw_get(path: str, params: dict | None = None) -> dict | list:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.get(f"{GATEWAY_URL}{path}", params=params or {})
        r.raise_for_status()
        return r.json()


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def discord_send(channel_id: str, content: str) -> str:
    """
    Post a message to a Discord text channel.

    Args:
        channel_id: Discord channel snowflake ID (e.g. '1234567890123456789').
        content: Message text (Discord markdown supported, max 2000 chars).

    Returns:
        'ok:<message_id>' on success or the error description.
    """
    if not DISCORD_BOT_TOKEN:
        return "error: DISCORD_BOT_TOKEN not set"
    resp = _d_post(f"/channels/{channel_id}/messages", {"content": content[:2000]})
    if "id" in resp:
        return f"ok:{resp['id']}"
    return f"error: {resp.get('message', resp)}"


@mcp.tool()
def discord_read(channel_id: str, limit: int = 10) -> str:
    """
    Read recent messages from a Discord text channel.

    Args:
        channel_id: Discord channel snowflake ID.
        limit: Number of messages (1–100). Default: 10.

    Returns:
        Formatted list of messages with timestamp, author, and content.
    """
    if not DISCORD_BOT_TOKEN:
        return "error: DISCORD_BOT_TOKEN not set"
    msgs = _d_get(f"/channels/{channel_id}/messages", {"limit": min(limit, 100)})
    if isinstance(msgs, dict) and "message" in msgs:
        return f"error: {msgs['message']}"
    lines = []
    for m in (msgs or []):
        ts = (m.get("timestamp") or "")[:16]
        author = m.get("author", {}).get("username", "?")
        content = (m.get("content") or "")[:200]
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines) if lines else "(no messages)"


@mcp.tool()
def discord_sense(text: str, channel_id: str = "", session_id: str = "discord-mcp") -> str:
    """
    Route text through the ZANA cognitive pipeline. If channel_id is provided,
    posts the response to that Discord channel.

    Args:
        text: Input to process.
        channel_id: Discord channel to post the response to (optional).
        session_id: ZANA session ID for memory continuity.

    Returns:
        ZANA's response text.
    """
    try:
        result = _gw_post("/sense/text", {"text": text, "session_id": session_id})
        response = result.get("response_text") or result.get("text") or "(no response)"
        surprise = result.get("kalman_surprise", 0)
        reply = response + (f"\n-# surprise: {surprise:.2f}" if surprise > 1.5 else "")
        if channel_id:
            discord_send(channel_id, f"🧠 **ZANA:** {reply[:1990]}")
        return reply
    except Exception as e:
        return f"gateway_error: {e}"


@mcp.tool()
def discord_reason(fact: str, channel_id: str = "", remote: bool = False) -> str:
    """
    Trigger ZANA's symbolic reasoning engine with a structured fact.

    Args:
        fact: Fact in 'key=value' format (e.g. 'machine_health_avg=0.3').
        channel_id: Discord channel to post results to (optional).
        remote: Escalate to swarm if no local rules fire.

    Returns:
        Summary of deductions from the reasoning engine.
    """
    k, _, v = fact.partition("=")
    try:
        val: float | str = float(v)
    except ValueError:
        val = v
    try:
        result = _gw_post("/reason", {"fact": {"fact_key": k.strip(), "value": val},
                                       "remote_query": remote})
        deductions = result.get("deductions", [])
        if not deductions:
            msg = f"No deductions for `{fact}`."
        else:
            lines = [f"🧠 **Reasoning: {fact}**\n"]
            for d in deductions:
                lines.append(f"• **{d.get('rule')}** ({d.get('confidence', 0):.0%}) → {d.get('conclusion')}")
                if d.get("action"):
                    lines.append(f"  ⚡ `{d['action']}`")
            msg = "\n".join(lines)
        if channel_id:
            discord_send(channel_id, msg[:2000])
        return msg
    except Exception as e:
        return f"error: {e}"


@mcp.tool()
def discord_recall(n: int = 5, channel_id: str = "") -> str:
    """
    Fetch the last N episodic memories from ZANA.

    Args:
        n: Number of memories (1–20).
        channel_id: Discord channel to post to (optional).

    Returns:
        Formatted episodic memory log.
    """
    try:
        records = _gw_get("/memory/episodic", {"limit": min(n, 20)})
        if not records:
            return "No episodic records yet."
        lines = [f"📚 **Last {len(records)} memories:**\n"]
        for r in records:
            ts = (r.get("created_at") or "")[:16]
            role = "user" if r.get("role") == "user" else "ZANA"
            content = (r.get("content") or "")[:120]
            lines.append(f"`{ts}` **{role}:** {content}")
        msg = "\n".join(lines)
        if channel_id:
            discord_send(channel_id, msg[:2000])
        return msg
    except Exception as e:
        return f"error: {e}"


@mcp.tool()
def discord_status(channel_id: str = "") -> str:
    """
    Fetch ZANA system health and optionally post to a Discord channel.

    Args:
        channel_id: Discord channel to post to (optional).

    Returns:
        Health summary.
    """
    try:
        data = _gw_get("/health")
        backends = data.get("backends", {})
        icon = {"stt": "🎤", "tts": "🔊", "llm": "🧠", "vision": "👁️", "kalman": "📐", "armor": "🛡️"}
        lines = ["⚙️ **ZANA Gateway — Online**\n"]
        lines += [f"{icon.get(k, '·')} `{k}`: {v}" for k, v in backends.items()]
        msg = "\n".join(lines)
        if channel_id:
            discord_send(channel_id, msg)
        return msg
    except Exception:
        return "⚠️ Gateway offline."


@mcp.tool()
def discord_channels(guild_id: str) -> str:
    """
    List all text channels in a Discord server.

    Args:
        guild_id: Discord server (guild) snowflake ID.

    Returns:
        List of text channel names and IDs.
    """
    if not DISCORD_BOT_TOKEN:
        return "error: DISCORD_BOT_TOKEN not set"
    channels = _d_get(f"/guilds/{guild_id}/channels")
    if isinstance(channels, dict):
        return f"error: {channels.get('message', channels)}"
    text_channels = [c for c in channels if c.get("type") == 0]
    return "\n".join(f"#{c['name']} ({c['id']})" for c in text_channels) or "(no text channels)"


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
