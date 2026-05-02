"""
zana wisdom — Auto-WisdomRules inbox CLI.

  zana wisdom inbox     — list pending proposals
  zana wisdom mine      — trigger trajectory mining
  zana wisdom approve   — approve a proposal by ID
  zana wisdom reject    — reject a proposal by ID
"""

from __future__ import annotations

import httpx
from cli.tui.theme import console

GATEWAY_URL = "http://localhost:54446"
_TIMEOUT = httpx.Timeout(120.0, connect=5.0)


def cmd_wisdom_inbox() -> None:
    try:
        r = httpx.get(f"{GATEWAY_URL}/wisdom/inbox", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error conectando al gateway: {e}[/warning]")
        console.print("[muted]¿Está ZANA corriendo? Ejecuta [accent]zana start[/accent] primero.[/muted]")
        return

    pending = data.get("pending", [])
    stats = data.get("stats", {})

    console.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print(
        f"[bold white]  Wisdom Inbox — {len(pending)} pendiente(s)[/bold white]  "
        f"[muted]✅ {stats.get('approved', 0)} aprobadas  ·  🗑️ {stats.get('rejected', 0)} rechazadas[/muted]"
    )
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n")

    if not pending:
        console.print("[muted]Sin propuestas pendientes.[/muted]")
        console.print("  Usa [accent]zana wisdom mine[/accent] para extraer patrones de tus sesiones.\n")
        return

    for p in pending:
        conf = p.get("confidence", 0)
        bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
        console.print(f"  [bold]{p['name']}[/bold]  [muted][{p['id']}][/muted]")
        console.print(f"  Dominio: [accent]{p.get('domain', '?')}[/accent]  ·  Confianza: [primary]{bar}[/primary] {conf:.0%}")
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
    console.print(f"  [success]✓[/success]  Trayectorias analizadas: [bold]{mined}[/bold]")
    console.print(f"  [success]✓[/success]  Nuevas propuestas: [bold]{proposed}[/bold]")
    if proposed > 0:
        console.print("\n  Usa [accent]zana wisdom inbox[/accent] para revisarlas.\n")
    else:
        console.print("\n  [muted]Sin nuevos patrones detectados. Acumula más sesiones.[/muted]\n")


def cmd_wisdom_approve(wisdom_id: str) -> None:
    try:
        r = httpx.post(f"{GATEWAY_URL}/wisdom/approve/{wisdom_id}", json={}, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    console.print(f"\n  [success]✅ Skill activada:[/success] [bold]{data.get('name', '?')}[/bold]")
    console.print(f"  ID en registry: [accent]{data.get('skill_id', '?')}[/accent]\n")


def cmd_wisdom_reject(wisdom_id: str) -> None:
    try:
        r = httpx.post(f"{GATEWAY_URL}/wisdom/reject/{wisdom_id}", timeout=_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        console.print(f"[warning]Error: {e}[/warning]")
        return

    console.print(f"\n  [muted]🗑️ Propuesta {wisdom_id} rechazada.[/muted]\n")
