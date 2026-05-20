"""
zana cloud — monetization CLI.

zana cloud status    Show current tier and subscription.
zana subscribe       Show pricing tiers and open waitlist.
"""

from __future__ import annotations

import webbrowser

import typer

from zana.tui.theme import console

PRICING_URL = "https://zana.vecanova.com/pricing"

_TIERS = [
    {
        "name": "Libre",
        "price": "$0/mo",
        "features": "CLI + SPROUT — offline, SQLite memory, 15 local intents",
        "highlight": False,
    },
    {
        "name": "Sovereign",
        "price": "$8/mo",
        "features": "Hosted gateway + semantic memory + cloud backup + multi-device sync",
        "highlight": True,
    },
    {
        "name": "Pro",
        "price": "$20/mo",
        "features": "Priority model routing + extended storage + dedicated support",
        "highlight": False,
    },
]


def cmd_cloud_status() -> None:
    """Show current tier, subscription status, and upgrade path."""
    from zana.core.memory_lite import is_sqlite_vec_available
    from zana.core.tier import Tier, detect_tier

    tier = detect_tier()
    vec = is_sqlite_vec_available()

    console.print()
    console.print("[bold]ZANA Cloud Status[/bold]")
    console.print("─" * 40)
    console.print(f"  Tier:           [accent]{tier.value.upper()}[/accent]")
    if vec and tier == Tier.SPROUT:
        console.print("  Semantic memory: [success]✓ sqlite-vec (GROVE path)[/success]")
    elif tier in (Tier.GROVE, Tier.FOREST):
        console.print("  Semantic memory: [success]✓ Active[/success]")
    else:
        console.print(
            "  Semantic memory: [muted]Not active — zana upgrade --grove[/muted]"
        )
    console.print("  Subscription:   [muted]Libre (free)[/muted]")
    console.print("─" * 40)
    console.print("  Upgrade: [primary]zana subscribe[/primary]")
    console.print()


def cmd_subscribe() -> None:
    """Display pricing tiers and open the waitlist page."""
    console.print()
    console.print("[bold]ZANA Tiers[/bold]")
    console.print("─" * 55)

    for t in _TIERS:
        name = t["name"]
        price = t["price"]
        features = t["features"]
        if t["highlight"]:
            console.print(
                f"  [accent]{name:<12}[/accent] [bold]{price:<10}[/bold] {features}"
            )
        else:
            console.print(
                f"  {name:<12} [muted]{price:<10}[/muted] [muted]{features}[/muted]"
            )

    console.print("─" * 55)
    console.print(f"  Join waitlist: [primary]{PRICING_URL}[/primary]")
    console.print()

    try:
        open_browser = typer.confirm("  Open in browser?", default=True)
        if open_browser:
            webbrowser.open(PRICING_URL)
            console.print("[muted]Opened in default browser.[/muted]")
    except (KeyboardInterrupt, Exception):
        pass
    console.print()
