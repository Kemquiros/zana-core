"""
zana sentinel — Sentinel Event Bus CLI.

  zana sentinel status    — bus health + event type counts
  zana sentinel events    — recent events from ring buffer
  zana sentinel ledger    — last N entries from Civic Ledger
"""

from __future__ import annotations

import json
import httpx
from cli.tui.theme import console

GATEWAY_URL = "http://localhost:54446"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_EVENT_ICONS = {
    "PreToolUse":       "⚔️ ",
    "PostToolUse":      "✅ ",
    "SkillActivation":  "🧠 ",
    "ZSyncRequest":     "🌐 ",
    "ExternalAPI":      "☁️ ",
    "MemoryWrite":      "💾 ",
    "CivicLedgerEntry": "📜 ",
    "AeonEvolution":    "🌟 ",
}


def cmd_sentinel_status() -> None:
    try:
        r = httpx.get(f"{GATEWAY_URL}/sentinel/status", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        console.print("[muted]¿Está ZANA corriendo? Ejecuta [accent]zana start[/accent] primero.[/muted]")
        return

    console.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print(f"[bold white]  Sentinel Event Bus — {data.get('status', '?').upper()}[/bold white]")
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n")

    stats = data.get("stats", {})
    total = stats.get("total", 0)
    console.print(f"  Eventos totales procesados: [bold]{total}[/bold]")
    console.print(f"  Entradas en Civic Ledger:   [bold]{data.get('ledger_entries', 0)}[/bold]\n")

    console.print("  [muted]Por tipo:[/muted]")
    for et in data.get("event_types", []):
        icon = _EVENT_ICONS.get(et, "· ")
        count = stats.get(et, 0)
        bar = "█" * min(count, 20) + ("" if count == 0 else "")
        console.print(f"  {icon} [accent]{et:<22}[/accent] {count:>5}  [muted]{bar}[/muted]")
    console.print()


def cmd_sentinel_events(limit: int = 20, event_type: str | None = None) -> None:
    params: dict = {"limit": limit}
    if event_type:
        params["event_type"] = event_type
    try:
        r = httpx.get(f"{GATEWAY_URL}/sentinel/events", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    events = data.get("events", [])
    total = data.get("total_in_buffer", 0)

    console.print(f"\n  [bold]Últimos {len(events)} eventos[/bold]  [muted](buffer: {total})[/muted]\n")
    for ev in events:
        icon = _EVENT_ICONS.get(ev.get("type", ""), "· ")
        ts = (ev.get("timestamp", ""))[:19].replace("T", " ")
        session = ev.get("session_id", "?")[:12]
        keys = ", ".join(ev.get("payload_keys", []))
        h = ev.get("civic_hash", "")[:12]
        console.print(
            f"  {icon}[accent]{ev.get('type', '?'):<22}[/accent]"
            f"  [muted]{ts}[/muted]"
            f"  [muted]session={session}[/muted]"
            f"  [muted]hash={h}[/muted]"
        )
        if keys:
            console.print(f"    [muted]payload: {keys}[/muted]")
    console.print()


def cmd_sentinel_ledger(limit: int = 20) -> None:
    try:
        r = httpx.get(f"{GATEWAY_URL}/sentinel/ledger", params={"limit": limit}, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    entries = data.get("entries", [])
    total = data.get("total", 0)

    console.print(f"\n  [bold]Civic Ledger — últimas {len(entries)} entradas[/bold]  [muted](total: {total})[/muted]\n")
    for entry in entries:
        icon = _EVENT_ICONS.get(entry.get("event_type", ""), "· ")
        ts = (entry.get("timestamp", ""))[:19].replace("T", " ")
        h = entry.get("civic_hash", "")[:16]
        et = entry.get("event_type", "?")
        console.print(
            f"  {icon}[accent]{et:<22}[/accent]"
            f"  [muted]{ts}[/muted]"
            f"  [primary]{h}...[/primary]"
        )
    console.print()
