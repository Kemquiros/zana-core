"""
zana sentinel — Sentinel Event Bus CLI.

  zana sentinel status    — bus health + event type counts
  zana sentinel events    — recent events from ring buffer
  zana sentinel ledger    — last N entries from Civic Ledger
"""

from __future__ import annotations

import httpx

from zana.core.sentinel_lite import get_sentinel_db
from zana.tui.theme import console

GATEWAY_URL = "http://localhost:54446"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_OFFLINE_TIMEOUT = httpx.Timeout(2.0, connect=2.0)

_EVENT_ICONS = {
    "PreToolUse": "⚔️ ",
    "PostToolUse": "✅ ",
    "SkillActivation": "🧠 ",
    "ZSyncRequest": "🌐 ",
    "ExternalAPI": "☁️ ",
    "MemoryWrite": "💾 ",
    "CivicLedgerEntry": "📜 ",
    "AeonEvolution": "🌟 ",
}


def _is_gateway_online() -> bool:
    """Return True if the ZANA Gateway is reachable, False otherwise.

    Uses a short 2-second timeout so offline detection is near-instant.
    """
    try:
        r = httpx.get(f"{GATEWAY_URL}/sentinel/status", timeout=_OFFLINE_TIMEOUT)
        return r.is_success
    except Exception:
        return False


def cmd_sentinel_status() -> None:
    if _is_gateway_online():
        # --- Gateway path (BLOOM / GLOW tier) ---
        try:
            r = httpx.get(f"{GATEWAY_URL}/sentinel/status", timeout=_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            console.print(f"[warning]Error: {e}[/warning]")
            console.print(
                "[muted]Is ZANA running? Execute [accent]zana start[/accent] first.[/muted]"
            )
            return

        console.print(
            "\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]"
        )
        console.print(
            f"[bold white]  Sentinel Event Bus — {data.get('status', '?').upper()}[/bold white]"
        )
        console.print(
            "[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n"
        )

        stats = data.get("stats", {})
        total = stats.get("total", 0)
        console.print(f"  Total events processed: [bold]{total}[/bold]")
        console.print(
            f"  Civic Ledger entries:   [bold]{data.get('ledger_entries', 0)}[/bold]\n"
        )

        console.print("  [muted]By type:[/muted]")
        for et in data.get("event_types", []):
            icon = _EVENT_ICONS.get(et, "· ")
            count = stats.get(et, 0)
            bar = "█" * min(count, 20) + ("" if count == 0 else "")
            console.print(
                f"  {icon} [accent]{et:<22}[/accent] {count:>5}  [muted]{bar}[/muted]"
            )
        console.print()
    else:
        # --- Offline path (SPROUT tier) ---
        db = get_sentinel_db()
        stats = db.stats()
        db.close()

        console.print(
            "\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]"
        )
        console.print(
            "[bold white]  Sentinel Event Bus — OFFLINE (SPROUT mode)[/bold white]"
        )
        console.print(
            "[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n"
        )
        console.print(
            "[muted]⚡ Gateway unreachable — reading local sentinel DB[/muted]\n"
        )

        total = stats.get("total", 0)
        console.print(f"  Total events (local):   [bold]{total}[/bold]")

        by_type = stats.get("by_type", {})
        if by_type:
            console.print("\n  [muted]By type:[/muted]")
            for et, count in by_type.items():
                icon = _EVENT_ICONS.get(et, "· ")
                bar = "█" * min(count, 20)
                console.print(
                    f"  {icon} [accent]{et:<22}[/accent] {count:>5}  [muted]{bar}[/muted]"
                )
        else:
            console.print("  [muted]No local events recorded yet.[/muted]")
        console.print()


def cmd_sentinel_events(limit: int = 20, event_type: str | None = None) -> None:
    if _is_gateway_online():
        # --- Gateway path (BLOOM / GLOW tier) ---
        params: dict = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
        try:
            r = httpx.get(
                f"{GATEWAY_URL}/sentinel/events", params=params, timeout=_TIMEOUT
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            console.print(f"[warning]Error: {e}[/warning]")
            return

        events = data.get("events", [])
        total = data.get("total_in_buffer", 0)

        console.print(
            f"\n  [bold]Last {len(events)} events[/bold]  [muted](buffer: {total})[/muted]\n"
        )
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
    else:
        # --- Offline path (SPROUT tier) ---
        db = get_sentinel_db()
        events = db.events(limit=limit, event_type=event_type)
        db.close()

        console.print("[muted]⚡ SPROUT mode — reading from local sentinel DB[/muted]")
        console.print(f"\n  [bold]Last {len(events)} events (local)[/bold]\n")
        for ev in events:
            icon = _EVENT_ICONS.get(ev.get("event_type", ""), "· ")
            ts = ev.get("timestamp", "")[:19].replace("T", " ")
            h = ev.get("civic_hash", "")[:12]
            ph = ev.get("payload_hash", "")[:12]
            console.print(
                f"  {icon}[accent]{ev.get('event_type', '?'):<22}[/accent]"
                f"  [muted]{ts}[/muted]"
                f"  [muted]payload={ph}[/muted]"
                f"  [muted]hash={h}[/muted]"
            )
        if not events:
            console.print("  [muted]No local events recorded yet.[/muted]")
        console.print()


def cmd_sentinel_threats(top_n: int = 10) -> None:
    """Display threat analytics dashboard from Civic Ledger."""
    from rich.table import Table

    blocked_types = {
        "ShellForbiddenCommand",
        "ShellInvalidParam",
        "ShellMissingParam",
        "ShellUnknownIntent",
        "ZNetworkPingFailed",
    }
    executed_types = {"ShellExecuted"}

    db = get_sentinel_db()
    summary = db.threat_summary(top_n=top_n)
    db.close()

    total = summary["total"]
    blocked = summary["blocked_count"]
    cancelled = summary["cancelled_count"]
    executed = summary["executed_count"]
    block_rate = summary["block_rate"]
    by_type: dict = summary["by_type"]
    last_ts: str | None = summary["last_event_ts"]

    # ── Header ────────────────────────────────────────────────────────────────
    console.print(
        "\n[bold]Sentinel Threat Dashboard[/bold]  [muted](Civic Ledger analysis)[/muted]"
    )

    if total == 0:
        console.print("[muted]No hay eventos en el Civic Ledger todavía.[/muted]\n")
        return

    # ── Summary row ───────────────────────────────────────────────────────────
    block_pct = f"{block_rate * 100:.1f}%" if block_rate > 0 else "0.0%"
    console.print(
        f"  Total events: [bold]{total}[/bold]"
        f"  ·  Blocked: [bold red]{blocked}[/bold red] ({block_pct})"
        f"  ·  Cancelled: [bold yellow]{cancelled}[/bold yellow]"
        f"  ·  Executed: [bold green]{executed}[/bold green]"
    )
    console.print()

    # ── Event Distribution table ──────────────────────────────────────────────
    max_count = max(by_type.values()) if by_type else 1

    table = Table(title="Event Distribution", show_header=True, header_style="bold")
    table.add_column("Event Type", style="accent", min_width=28)
    table.add_column("Count", justify="right", min_width=6)
    table.add_column("Bar", min_width=22)

    for et, cnt in by_type.items():
        bar_len = max(1, round(cnt / max_count * 20)) if cnt > 0 else 0
        bar = "█" * bar_len

        if et in blocked_types:
            row_style = "red"
        elif et in executed_types:
            row_style = "green"
        else:
            row_style = "yellow"

        table.add_row(
            f"[{row_style}]{et}[/{row_style}]",
            f"[{row_style}]{cnt}[/{row_style}]",
            f"[{row_style}]{bar}[/{row_style}]",
        )

    console.print(table)

    # ── High block rate warning ───────────────────────────────────────────────
    if block_rate > 0.30:
        console.print(
            "[error]⚠ Block rate > 30% — revisar configuración ShellGuard[/error]"
        )

    # ── Last event timestamp ──────────────────────────────────────────────────
    if last_ts:
        console.print(
            f"\n  [muted]Last event: {last_ts[:19].replace('T', ' ')}[/muted]"
        )
    console.print()


def cmd_sentinel_ledger(limit: int = 20) -> None:
    if _is_gateway_online():
        # --- Gateway path (BLOOM / GLOW tier) ---
        try:
            r = httpx.get(
                f"{GATEWAY_URL}/sentinel/ledger",
                params={"limit": limit},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            console.print(f"[warning]Error: {e}[/warning]")
            return

        entries = data.get("entries", [])
        total = data.get("total", 0)

        console.print(
            f"\n  [bold]Civic Ledger — last {len(entries)} entries[/bold]  [muted](total: {total})[/muted]\n"
        )
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
    else:
        # --- Offline path (SPROUT tier) ---
        db = get_sentinel_db()
        entries = db.ledger(limit=limit)
        db.close()

        console.print("[muted]⚡ SPROUT mode — reading from local sentinel DB[/muted]")
        console.print(
            f"\n  [bold]Civic Ledger — last {len(entries)} entries (local)[/bold]\n"
        )
        for entry in entries:
            icon = _EVENT_ICONS.get(entry.get("event_type", ""), "· ")
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            h = entry.get("civic_hash", "")[:16]
            et = entry.get("event_type", "?")
            console.print(
                f"  {icon}[accent]{et:<22}[/accent]"
                f"  [muted]{ts}[/muted]"
                f"  [primary]{h}...[/primary]"
            )
        if not entries:
            console.print(
                "  [muted]No Civic Ledger entries recorded locally yet.[/muted]"
            )
        console.print()
