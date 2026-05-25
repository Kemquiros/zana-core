"""
zana wisdom — Auto-WisdomRules inbox CLI.

  zana wisdom inbox     — list pending proposals
  zana wisdom mine      — trigger trajectory mining
  zana wisdom approve   — approve a proposal by ID
  zana wisdom reject    — reject a proposal by ID
"""

from __future__ import annotations

import httpx

from zana.tui.theme import console

GATEWAY_URL = "http://localhost:54446"
_TIMEOUT = httpx.Timeout(120.0, connect=5.0)


def _is_gateway_online() -> bool:
    """Return True if the Gateway responds within 2 seconds."""
    try:
        httpx.get(f"{GATEWAY_URL}/health", timeout=2.0).raise_for_status()
        return True
    except Exception:
        return False


def cmd_wisdom_inbox() -> None:
    if not _is_gateway_online():
        from zana.core.wisdom_queue import WisdomQueue

        q = WisdomQueue()
        pending = q.inbox()
        stats = q.stats()
        console.print("[muted]⚡ SPROUT mode — reading from local wisdom queue[/muted]")
        console.print(
            "\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]"
        )
        console.print(
            f"[bold white]  Wisdom Inbox — {len(pending)} pending[/bold white]  "
            f"[muted]✅ {stats['approved']} approved  ·  🗑️ {stats['rejected']} rejected[/muted]"
        )
        console.print(
            "[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n"
        )
        if not pending:
            console.print("[muted]No pending proposals in local queue.[/muted]")
            console.print(
                "  Use [accent]zana wisdom mine[/accent] (requires Gateway) to generate proposals.\n"
            )
            return
        for p in pending:
            conf = p.get("confidence", 0)
            bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            console.print(
                f"  [bold]{p.get('name', '?')}[/bold]  [muted][{p.get('id', '?')}][/muted]"
            )
            console.print(
                f"  Domain: [accent]{p.get('domain', '?')}[/accent]  ·  Confidence: [primary]{bar}[/primary] {conf:.0%}"
            )
            console.print(
                f"  [success]zana wisdom approve {p.get('id', '?')}[/success]  "
                f"[warning]zana wisdom reject {p.get('id', '?')}[/warning]\n"
            )
        return

    try:
        r = httpx.get(f"{GATEWAY_URL}/wisdom/inbox", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error conectando al gateway: {e}[/warning]")
        console.print(
            "[muted]¿Está ZANA corriendo? Ejecuta [accent]zana start[/accent] primero.[/muted]"
        )
        return

    pending = data.get("pending", [])
    stats = data.get("stats", {})

    console.print(
        "\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]"
    )
    console.print(
        f"[bold white]  Wisdom Inbox — {len(pending)} pendiente(s)[/bold white]  "
        f"[muted]✅ {stats.get('approved', 0)} aprobadas  ·  🗑️ {stats.get('rejected', 0)} rechazadas[/muted]"
    )
    console.print(
        "[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n"
    )

    if not pending:
        console.print("[muted]Sin propuestas pendientes.[/muted]")
        console.print(
            "  Usa [accent]zana wisdom mine[/accent] para extraer patrones de tus sesiones.\n"
        )
        return

    for p in pending:
        conf = p.get("confidence", 0)
        bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
        console.print(f"  [bold]{p['name']}[/bold]  [muted][{p['id']}][/muted]")
        console.print(
            f"  Dominio: [accent]{p.get('domain', '?')}[/accent]  ·  Confianza: [primary]{bar}[/primary] {conf:.0%}"
        )
        if p.get("trigger"):
            console.print(f"  Trigger: [muted]{p['trigger']}[/muted]")
        if p.get("steps"):
            for i, s in enumerate(p["steps"][:3], 1):
                console.print(f"    {i}. {s}")
        console.print(
            f"  [success]zana wisdom approve {p['id']}[/success]  "
            f"[warning]zana wisdom reject {p['id']}[/warning]\n"
        )


def cmd_wisdom_mine() -> None:
    if not _is_gateway_online():
        console.print(
            "[muted]⚡ SPROUT mode — Gateway required for trajectory mining.[/muted]"
        )
        console.print(
            "\n  Offline mining is not yet available. Start the Gateway with [accent]zana start[/accent]"
            "\n  to analyze session trajectories and generate WisdomRule proposals."
            "\n\n  In the meantime, explore your local memory:"
            "\n  [accent]zana memory search <query>[/accent]  ·  [accent]zana memory recall[/accent]\n"
        )
        return

    console.print("\n[muted]Analizando trayectorias de sesión...[/muted]")
    try:
        r = httpx.post(f"{GATEWAY_URL}/wisdom/mine", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    mined = data.get("mined", 0)
    proposed = data.get("proposed", 0)
    console.print(
        f"  [success]✓[/success]  Trayectorias analizadas: [bold]{mined}[/bold]"
    )
    console.print(f"  [success]✓[/success]  Nuevas propuestas: [bold]{proposed}[/bold]")
    if proposed > 0:
        console.print("\n  Usa [accent]zana wisdom inbox[/accent] para revisarlas.\n")
    else:
        console.print(
            "\n  [muted]Sin nuevos patrones detectados. Acumula más sesiones.[/muted]\n"
        )


def cmd_wisdom_approve(wisdom_id: str) -> None:
    if not _is_gateway_online():
        from zana.core.wisdom_queue import WisdomQueue

        q = WisdomQueue()
        item = q.approve(wisdom_id)
        if item:
            console.print(
                f"\n  [success]✅ Approved:[/success] [bold]{item.get('name', wisdom_id)}[/bold]"
            )
            console.print("  [muted]⚡ SPROUT mode — stored in local queue[/muted]\n")
        else:
            console.print(
                f"\n  [error]✗ No pending proposal with id={wisdom_id}[/error]\n"
            )
        return

    try:
        r = httpx.post(
            f"{GATEWAY_URL}/wisdom/approve/{wisdom_id}", json={}, timeout=_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    console.print(
        f"\n  [success]✅ Skill activada:[/success] [bold]{data.get('name', '?')}[/bold]"
    )
    console.print(f"  ID en registry: [accent]{data.get('skill_id', '?')}[/accent]\n")


def _audit_wisdom(event_type: str, rule: dict) -> None:
    """Write a Civic Ledger entry for a wisdom event."""
    import hashlib
    import json

    try:
        from zana.core.sentinel_lite import SentinelLiteDB

        payload = json.dumps(rule, sort_keys=True, ensure_ascii=False).encode("utf-8")
        h = "sha256:" + hashlib.sha256(payload).hexdigest()[:16]
        db = SentinelLiteDB()
        db.record(event_type, payload_hash=h, civic_hash=h)
    except Exception:
        pass  # Audit failures must never break the main flow


def cmd_wisdom_propose(text: str, console=None, confidence: float = 0.85) -> None:
    """Create a WisdomRule candidate from free text and add to pending queue."""
    import re
    from datetime import UTC, datetime

    from zana.core.wisdom_queue import WisdomQueue

    if console is None:
        from zana.tui.theme import console as _console

        console = _console

    text = text.strip()
    if not text:
        console.print("[warning]Empty rule text — nothing proposed.[/warning]")
        return

    # Generate ID from first 6 words, slugified
    words = re.findall(r"[a-záéíóúüñ\w]+", text.lower())[:6]
    rule_id = "-".join(words)[:40] if words else "proposed-rule"
    rule_id = re.sub(r"[^a-z0-9\-]", "-", rule_id)

    # First sentence as name (truncated to 60 chars)
    name = re.split(r"[.!?]", text)[0].strip()[:60]

    proposal = {
        "id": rule_id,
        "name": name,
        "domain": "general",
        "confidence": 0.75,
        "trigger": text,
        "steps": [text],
        "created_at": datetime.now(UTC).isoformat(),
    }

    result = WisdomQueue().add(proposal)
    if result == "duplicate":
        console.print(
            "[warning]⚠ Regla similar ya existe (ratio > 85%). No añadida.[/warning]"
        )
    elif result == "auto_approved":
        console.print(
            f"[success]✓ Regla auto-aprobada (confianza ≥ 90%): '{proposal['name']}'[/success]"
        )
        console.print("[dim]Alta confianza → absorción directa al Civic Ledger.[/dim]")
        _audit_wisdom("WisdomAutoApproved", proposal)
    else:
        console.print(
            f"[success]✓ Regla propuesta: '{proposal['name']}' (confianza: {proposal['confidence']:.0%})[/success]"
        )
        console.print("[dim]Usa 'zana wisdom inbox' para revisar y aprobar.[/dim]")


def cmd_wisdom_stats(console=None) -> None:
    """Show WisdomQueue absorption analytics."""
    from zana.core.wisdom_queue import WisdomQueue

    if console is None:
        from zana.tui.theme import console as _console

        console = _console

    from rich.table import Table

    s = WisdomQueue().stats()

    if s["total_proposed"] == 0:
        console.print(
            "[muted]No hay WisdomRules todavía. Usa 'zana wisdom propose \"...\"'[/muted]"
        )
        return

    console.print("\n[bold]WisdomRule Analytics[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Pending", justify="right")
    table.add_column("Approved", justify="right")
    table.add_column("Rejected", justify="right")
    table.add_column("Auto-approved", justify="right")
    table.add_column("Absorption Rate", justify="right")
    table.add_column("Avg Confidence", justify="right")

    table.add_row(
        str(s["pending_count"]),
        str(s["approved_count"]),
        str(s["rejected_count"]),
        str(s["auto_approved_count"]),
        f"{s['absorption_rate']:.0%}",
        f"{s['avg_confidence']:.0%}",
    )
    console.print(table)

    if s["absorption_rate"] > 0.70:
        console.print(
            f"[success]✓ Alta absorción de sabiduría ({s['absorption_rate']:.0%})[/success]"
        )
    if s["auto_approved_count"] > 0:
        console.print(
            f"[dim]{s['auto_approved_count']} reglas auto-aprobadas por alta confianza.[/dim]"
        )


def cmd_wisdom_reject(wisdom_id: str) -> None:
    if not _is_gateway_online():
        from zana.core.wisdom_queue import WisdomQueue

        q = WisdomQueue()
        found = q.reject(wisdom_id)
        if found:
            console.print(
                f"\n  [muted]🗑️ Proposal {wisdom_id} rejected (local queue).[/muted]\n"
            )
        else:
            console.print(
                f"\n  [error]✗ No pending proposal with id={wisdom_id}[/error]\n"
            )
        return

    try:
        r = httpx.post(f"{GATEWAY_URL}/wisdom/reject/{wisdom_id}", timeout=_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    console.print(f"\n  [muted]🗑️ Propuesta {wisdom_id} rechazada.[/muted]\n")
