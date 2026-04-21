import json
import re
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from cli.tui.theme import console

SESSION_FILE = Path.home() / ".config" / "zana" / "session.json"

def _find_registry() -> Path:
    # 1. Explicit env override
    env = Path(typer.get_app_dir("zana")) if False else None
    import os
    if "ZANA_REGISTRY_PATH" in os.environ:
        return Path(os.environ["ZANA_REGISTRY_PATH"])
    # 2. User config override
    user_reg = Path.home() / ".config" / "zana" / "registry.json"
    if user_reg.exists():
        return user_reg
    # 3. Walk up from __file__ to find zana-core/aeons/registry.json
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "aeons" / "registry.json"
        if candidate.exists():
            return candidate
    # 4. Bundled default inside the package
    return Path(__file__).parent.parent / "data" / "registry.json"

REGISTRY_PATH = _find_registry()

COST_COLOR = {"low": "green", "medium": "yellow", "high": "red"}
LATENCY_ICON = {"fast": "⚡", "medium": "◎", "slow": "🐢"}


def _load_registry() -> dict:
    path = _find_registry()
    if not path.exists():
        console.print(f"[error]Registry not found. Set ZANA_REGISTRY_PATH or run from the zana-core directory.[/error]")
        raise typer.Exit(1)
    return json.loads(path.read_text())


def _load_session() -> dict:
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_session(data: dict) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(data, indent=2))


def _active_aeon_id() -> str:
    return _load_session().get("active_aeon", "herald")


def cmd_list() -> None:
    registry = _load_registry()
    active = _active_aeon_id()

    table = Table(
        show_header=True,
        header_style="header",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("",       width=2)
    table.add_column("ID",     style="bold white",  width=12)
    table.add_column("Name",   style="primary",      width=10)
    table.add_column("Model",  style="muted",        width=24)
    table.add_column("Cost",   width=8)
    table.add_column("Speed",  width=7)
    table.add_column("Tagline", style="muted")

    for aeon in registry["aeons"]:
        marker = "[accent]▶[/accent]" if aeon["id"] == active else " "
        cost_c = COST_COLOR.get(aeon["cost_tier"], "white")
        lat_i  = LATENCY_ICON.get(aeon["latency"], "?")
        table.add_row(
            marker,
            aeon["id"],
            f"{aeon['icon']} {aeon['name']}",
            aeon["model"],
            f"[{cost_c}]{aeon['cost_tier']}[/{cost_c}]",
            lat_i,
            aeon["tagline"],
        )

    console.print(Panel(table,
        title="[header] ZANA — AEON FLEET [/header]",
        subtitle=f"[muted]Active: [accent]{active}[/accent][/muted]",
        border_style="magenta",
        padding=(0, 1),
    ))


def cmd_use(aeon_id: str) -> None:
    registry = _load_registry()
    ids = [a["id"] for a in registry["aeons"]]

    if aeon_id not in ids:
        console.print(f"[error]Unknown Aeon '{aeon_id}'. Run `zana aeon list` to see options.[/error]")
        raise typer.Exit(1)

    aeon = next(a for a in registry["aeons"] if a["id"] == aeon_id)
    session = _load_session()
    prev = session.get("active_aeon", "herald")
    session["active_aeon"] = aeon_id
    _save_session(session)

    console.print(f"[muted]  {prev} →[/muted] [accent]{aeon['icon']} {aeon['name']}[/accent]")
    console.print(f"  [muted]{aeon['tagline']}[/muted]")
    console.print(f"  [muted]Model: {aeon['model']} · Cost: {aeon['cost_tier']} · Speed: {aeon['latency']}[/muted]")


def cmd_recommend(context: Optional[str] = None) -> None:
    registry = _load_registry()
    rules = registry["recommendation_rules"]

    if not context:
        # Read from stdin if no context given
        console.print("[muted]Describe what you need (Enter to skip):[/muted] ", end="")
        try:
            context = input("").strip()
        except (EOFError, KeyboardInterrupt):
            context = ""

    if not context:
        aeon_id = rules["default"]
        reason  = "No context — using default conversational Aeon."
    else:
        ctx_lower = context.lower()
        aeon_id, reason = _match_rules(ctx_lower, rules)

    aeon = next((a for a in registry["aeons"] if a["id"] == aeon_id), None)
    if not aeon:
        console.print(f"[error]Recommended Aeon '{aeon_id}' not found in registry.[/error]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[accent]{aeon['icon']}  {aeon['name']}[/accent]\n\n"
        f"[white]{aeon['tagline']}[/white]\n\n"
        f"[muted]Model:[/muted] {aeon['model']}\n"
        f"[muted]Reason:[/muted] {reason}",
        title="[header] RECOMMENDATION [/header]",
        border_style="magenta",
        padding=(1, 2),
    ))

    confirm = typer.confirm(f"  Switch to {aeon['name']}?", default=True)
    if confirm:
        cmd_use(aeon_id)


def _match_rules(ctx: str, rules: dict) -> tuple[str, str]:
    code_kw    = r"\b(code|implement|refactor|build|bug|function|class|test|script|dockerfile|api)\b"
    math_kw    = r"\b(calculat|analyz|math|formula|proof|statistic|model|equation|logic)\b"
    memory_kw  = r"\b(remember|recall|find|search|history|what did|last time|previous|stored)\b"
    security_kw= r"\b(security|password|pii|private|hack|inject|leak|compli)\b"
    research_kw= r"\b(research|paper|study|literature|explain in depth|deep dive|science|arxiv)\b"
    action_kw  = r"\b(run|execute|deploy|install|create file|delete|start|stop|docker)\b"
    monitor_kw = r"\b(monitor|watch|alert|notify|background|passive|detect)\b"

    checks = [
        (security_kw,  "sentinel",  "Security-sensitive terms detected."),
        (memory_kw,    "archivist", "Memory retrieval pattern detected."),
        (code_kw,      "forge",     "Code/engineering task detected."),
        (math_kw,      "analyst",   "Analytical/mathematical task detected."),
        (research_kw,  "scholar",   "Deep research task detected."),
        (action_kw,    "operator",  "System action task detected."),
        (monitor_kw,   "watcher",   "Monitoring/passive task detected."),
    ]

    for pattern, aeon_id, reason in checks:
        if re.search(pattern, ctx):
            return aeon_id, reason

    return rules.get("default", "herald"), "General task — conversational Aeon."


def cmd_status() -> None:
    registry = _load_registry()
    active_id = _active_aeon_id()
    aeon = next((a for a in registry["aeons"] if a["id"] == active_id), None)

    if not aeon:
        console.print(f"[warning]Active Aeon '{active_id}' not found in registry.[/warning]")
        raise typer.Exit(1)

    cost_c = COST_COLOR.get(aeon["cost_tier"], "white")
    lat_i  = LATENCY_ICON.get(aeon["latency"], "?")

    console.print(Panel(
        f"[accent]{aeon['icon']}  {aeon['name']}[/accent]    [muted](id: {aeon['id']})[/muted]\n\n"
        f"[white]{aeon['tagline']}[/white]\n\n"
        f"[muted]Model:[/muted]    {aeon['model']}\n"
        f"[muted]Cost:[/muted]     [{cost_c}]{aeon['cost_tier']}[/{cost_c}]\n"
        f"[muted]Speed:[/muted]    {lat_i} {aeon['latency']}\n"
        f"[muted]Tools:[/muted]    {', '.join(aeon['tools'])}",
        title="[header] ACTIVE AEON [/header]",
        border_style="magenta",
        padding=(1, 2),
    ))
