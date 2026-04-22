"""
ZANA MCP Server for Slack (zana-slack).

Exposes ZANA's cognitive capabilities as MCP tools consumable by any
MCP-compatible client (Claude Code, Claude Desktop, etc.).

Tools:
  slack_send         — post a message to any Slack channel
  slack_read         — read recent messages from a channel
  slack_sense        — route text to ZANA Gateway and post the response
  slack_reason       — trigger forward-chaining and post deductions
  slack_recall       — fetch episodic memories and post them
  slack_status       — post ZANA system health to a channel
  slack_channels     — list accessible channels

Run as MCP server:
  uv run mcp dev server.py                   # development inspector
  uv run python server.py                    # stdio transport (Claude Desktop)

Required env vars:
  SLACK_BOT_TOKEN     — xoxb-... (Bot User OAuth Token from api.slack.com)
  ZANA_GATEWAY_URL    — http://localhost:54446 (or remote)
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
GATEWAY_URL = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
DEFAULT_CHANNEL = os.getenv("ZANA_SLACK_DEFAULT_CHANNEL", "general")

mcp = FastMCP("zana-slack")

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


# ── Slack API helpers ─────────────────────────────────────────────────────────


def _slack_headers() -> dict:
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }


def _slack_post(endpoint: str, payload: dict) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(
            f"https://slack.com/api/{endpoint}", json=payload, headers=_slack_headers()
        )
        return r.json()


def _slack_get(endpoint: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.get(
            f"https://slack.com/api/{endpoint}", params=params, headers=_slack_headers()
        )
        return r.json()


def _gw_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(f"{GATEWAY_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


def _gw_get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.get(f"{GATEWAY_URL}{path}", params=params or {})
        r.raise_for_status()
        return r.json()


# ── MCP Tools ─────────────────────────────────────────────────────────────────


@mcp.tool()
def slack_send(channel: str, text: str) -> str:
    """
    Post a plain-text message to a Slack channel.

    Args:
        channel: Channel name (e.g. 'general') or ID (e.g. 'C0123456789').
        text: Message content (supports Slack mrkdwn formatting).

    Returns:
        'ok' on success or the Slack API error message.
    """
    if not SLACK_BOT_TOKEN:
        return "error: SLACK_BOT_TOKEN not set"
    resp = _slack_post("chat.postMessage", {"channel": channel, "text": text})
    return "ok" if resp.get("ok") else resp.get("error", "unknown_error")


@mcp.tool()
def slack_read(channel: str, limit: int = 10) -> str:
    """
    Read the most recent messages from a Slack channel.

    Args:
        channel: Channel name or ID.
        limit: Number of messages to retrieve (1–100). Default: 10.

    Returns:
        Formatted list of recent messages with timestamp, author, and text.
    """
    if not SLACK_BOT_TOKEN:
        return "error: SLACK_BOT_TOKEN not set"
    resp = _slack_get(
        "conversations.history", {"channel": channel, "limit": min(limit, 100)}
    )
    if not resp.get("ok"):
        return f"error: {resp.get('error', 'unknown')}"
    msgs = resp.get("messages", [])
    lines = []
    for m in msgs:
        ts = m.get("ts", "")[:10]
        user = m.get("user", m.get("bot_id", "?"))
        text = (m.get("text") or "")[:200]
        lines.append(f"[{ts}] {user}: {text}")
    return "\n".join(lines) if lines else "(no messages)"


@mcp.tool()
def slack_sense(text: str, channel: str = "", session_id: str = "slack-mcp") -> str:
    """
    Route text through the full ZANA cognitive pipeline and post the response
    back to Slack. If channel is provided, posts the response there.

    Args:
        text: The input to process (user message, query, observation).
        channel: Slack channel to post the response to (optional).
        session_id: ZANA session identifier for episodic memory continuity.

    Returns:
        ZANA's response text.
    """
    try:
        result = _gw_post("/sense/text", {"text": text, "session_id": session_id})
        response = result.get("response_text") or result.get("text") or "(no response)"
        result.get("response_emotion", "")
        surprise = result.get("kalman_surprise", 0)

        reply = response
        if surprise > 1.5:
            reply += f"\n_[surprise: {surprise:.2f}]_"

        if channel:
            slack_send(channel, f"🧠 *ZANA:* {reply}")

        return reply
    except Exception as e:
        return f"gateway_error: {e}"


@mcp.tool()
def slack_reason(fact: str, channel: str = "", remote: bool = False) -> str:
    """
    Trigger ZANA's symbolic reasoning engine with a structured fact and
    optionally post the deduction trace to a Slack channel.

    Args:
        fact: Fact in 'key=value' format (e.g. 'machine_health_avg=0.3').
        channel: Slack channel to post results to (optional).
        remote: If True, escalate to swarm if no local rules fire.

    Returns:
        Summary of deductions produced by the reasoning engine.
    """
    k, _, v = fact.partition("=")
    try:
        parsed_v: float | str = float(v)
    except ValueError:
        parsed_v = v
    try:
        result = _gw_post(
            "/reason",
            {
                "fact": {"fact_key": k.strip(), "value": parsed_v},
                "remote_query": remote,
            },
        )
        deductions = result.get("deductions", [])
        if not deductions:
            msg = f"No deductions for `{fact}`."
        else:
            lines = [f"🧠 *Reasoning: {fact}*\n"]
            for d in deductions:
                lines.append(
                    f"• *{d.get('rule')}* ({d.get('confidence', 0):.0%}) → {d.get('conclusion')}"
                )
                if d.get("action"):
                    lines.append(f"  ⚡ `{d['action']}`")
            msg = "\n".join(lines)
        if channel:
            slack_send(channel, msg)
        return msg
    except Exception as e:
        return f"error: {e}"


@mcp.tool()
def slack_recall(n: int = 5, channel: str = "") -> str:
    """
    Fetch the last N episodic memories from ZANA and optionally post them
    to a Slack channel.

    Args:
        n: Number of memories to retrieve (1–20).
        channel: Slack channel to post to (optional).

    Returns:
        Formatted episodic memory log.
    """
    try:
        records = _gw_get("/memory/episodic", {"limit": min(n, 20)})
        if not records:
            return "No episodic records yet."
        lines = [f"📚 *Last {len(records)} memories:*\n"]
        for r in records:
            ts = (r.get("created_at") or "")[:16]
            role = "user" if r.get("role") == "user" else "ZANA"
            content = (r.get("content") or "")[:120]
            lines.append(f"[{ts}] *{role}:* {content}")
        msg = "\n".join(lines)
        if channel:
            slack_send(channel, msg)
        return msg
    except Exception as e:
        return f"error: {e}"


@mcp.tool()
def slack_status(channel: str = "") -> str:
    """
    Fetch ZANA system health (ZFI + backends) and optionally post to Slack.

    Args:
        channel: Slack channel to post to (optional).

    Returns:
        Health summary string.
    """
    try:
        data = _gw_get("/health")
        backends = data.get("backends", {})
        icon_map = {
            "stt": "🎤",
            "tts": "🔊",
            "llm": "🧠",
            "vision": "👁️",
            "kalman": "📐",
            "armor": "🛡️",
        }
        lines = ["⚙️ *ZANA Gateway — Online*\n"]
        for k, v in backends.items():
            lines.append(f"{icon_map.get(k, '·')} `{k}`: {v}")
        msg = "\n".join(lines)
        if channel:
            slack_send(channel, msg)
        return msg
    except Exception:
        return "⚠️ Gateway offline."


@mcp.tool()
def slack_channels() -> str:
    """
    List all Slack channels the bot has access to.

    Returns:
        Comma-separated list of channel names and IDs.
    """
    if not SLACK_BOT_TOKEN:
        return "error: SLACK_BOT_TOKEN not set"
    resp = _slack_get(
        "conversations.list", {"limit": 200, "types": "public_channel,private_channel"}
    )
    if not resp.get("ok"):
        return f"error: {resp.get('error')}"
    channels = resp.get("channels", [])
    return "\n".join(f"#{c['name']} ({c['id']})" for c in channels) or "(no channels)"


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
