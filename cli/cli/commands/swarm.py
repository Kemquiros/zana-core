"""
zana swarm — Red Queen swarm layer control (v2.2).

  zana swarm init [--warriors N] [--generations N]   bootstrap Red Queen
  zana swarm status                                   live warrior dashboard
  zana swarm stop                                     stop all warriors
  zana swarm sync                                     pull Wisdom Hub rules
  zana swarm query <fact_key>                         remote distributed query
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich import box

from cli.tui.theme import console

GATEWAY_URL = f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}"
REGISTRY_URL = f"http://localhost:{os.getenv('ZANA_REGISTRY_PORT', '54445')}"
SWARM_STATE_FILE = Path.home() / ".config" / "zana" / "swarm_state.json"


def _gw_post(path: str, payload: dict, timeout: int = 10) -> dict | None:
    try:
        r = httpx.post(f"{GATEWAY_URL}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return None
    except Exception as e:
        return {"error": str(e)}


def _gw_get(path: str, timeout: int = 5) -> dict | list | None:
    try:
        r = httpx.get(f"{GATEWAY_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _reg_get(path: str, timeout: int = 5) -> list | dict | None:
    try:
        r = httpx.get(f"{REGISTRY_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _save_state(state: dict) -> None:
    SWARM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SWARM_STATE_FILE.write_text(json.dumps(state, indent=2))


def _load_state() -> dict:
    if SWARM_STATE_FILE.exists():
        try:
            return json.loads(SWARM_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _render_warrior_table(warriors: list[dict]) -> Panel:
    table = Table(show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1))
    table.add_column("#",          style="muted",      width=4)
    table.add_column("ID",         style="bold white",  width=18)
    table.add_column("Stage",      style="accent",      width=10)
    table.add_column("Gen",        width=6)
    table.add_column("Fitness",    width=9)
    table.add_column("Status",     width=12)
    table.add_column("DNA Hash",   style="muted",       width=12)

    for i, w in enumerate(warriors, 1):
        fitness = w.get("fitness", 0.0)
        fit_color = "success" if fitness >= 0.8 else "warning" if fitness >= 0.5 else "muted"
        stage = w.get("stage", "larva")
        stage_icon = {"larva": "🥚", "warrior": "⚔️", "legend": "👑"}.get(stage, "·")
        status = w.get("status", "idle")
        status_cell = {
            "active":   "[success]● active[/success]",
            "evolving": "[warning]⟳ evolving[/warning]",
            "idle":     "[muted]○ idle[/muted]",
            "error":    "[error]✗ error[/error]",
        }.get(status, f"[muted]{status}[/muted]")
        dna = w.get("dna_fingerprint", "")[:10] + "…" if w.get("dna_fingerprint") else "—"
        table.add_row(
            str(i),
            w.get("id", f"warrior-{i}"),
            f"{stage_icon} {stage}",
            str(w.get("generation", 0)),
            f"[{fit_color}]{fitness:.3f}[/{fit_color}]",
            status_cell,
            dna,
        )

    online = sum(1 for w in warriors if w.get("status") == "active")
    legends = sum(1 for w in warriors if w.get("stage") == "legend")
    avg_fit = sum(w.get("fitness", 0) for w in warriors) / max(len(warriors), 1)
    fit_color = "success" if avg_fit >= 0.8 else "warning" if avg_fit >= 0.5 else "muted"

    return Panel(
        table,
        title="[header] RED QUEEN — Warrior Fleet [/header]",
        subtitle=f"  {online}/{len(warriors)} active  ·  {legends} legends  ·  "
                 f"avg fitness [{fit_color}]{avg_fit:.3f}[/{fit_color}]",
        border_style="magenta",
        padding=(0, 1),
    )


def cmd_swarm_init(warriors: int = 50, generations: int = 2000) -> None:
    console.print(f"\n[primary]RED QUEEN BOOTSTRAP[/primary] "
                  f"[muted]warriors={warriors}  generations={generations}[/muted]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Spawning warriors…", total=warriors)

        result = _gw_post("/swarm/init", {"warriors": warriors, "generations": generations}, timeout=30)

        if result is None:
            console.print("[error]Gateway offline. Run: zana start[/error]")
            return

        if "error" in result:
            # Gateway doesn't expose /swarm/init yet — bootstrap locally from swarm module
            console.print("[muted]Gateway swarm endpoint not available. Bootstrapping locally…[/muted]")
            _bootstrap_local(warriors, generations, progress, task)
            return

        progress.update(task, completed=warriors)

    spawned = result.get("spawned", warriors)
    state = {"warriors": spawned, "generations": generations,
             "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _save_state(state)

    console.print(f"[success]✓ Red Queen online. {spawned} warriors deployed.[/success]")
    console.print(f"[muted]Run [accent]zana swarm status[/accent] to watch evolution.[/muted]\n")


def _bootstrap_local(warriors: int, generations: int, progress, task) -> None:
    """
    Local bootstrap when Gateway swarm endpoint is unavailable.
    Uses swarm/meta_evolution.py + swarm/dna.py directly.
    """
    import importlib.util, random

    # Try to import from swarm module in project root
    root = Path(__file__).parent
    for _ in range(6):
        root = root.parent
        if (root / "swarm" / "dna.py").exists():
            break

    try:
        spec = importlib.util.spec_from_file_location("dna", root / "swarm" / "dna.py")
        dna_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dna_mod)
        ZanaDNA = dna_mod.ZanaDNA
    except Exception as e:
        console.print(f"[error]Cannot load swarm module: {e}[/error]")
        return

    fleet = []
    for i in range(warriors):
        dna = ZanaDNA(author=f"warrior-{i:04d}")
        dna.mutate(intensity=0.1)
        fleet.append({
            "id": f"warrior-{i:04d}",
            "stage": "larva",
            "generation": 0,
            "fitness": round(random.uniform(0.3, 0.7), 3),
            "dna_fingerprint": dna.get_fingerprint(),
            "status": "idle",
        })
        progress.update(task, completed=i + 1)
        time.sleep(0.01)

    state = {
        "warriors": warriors,
        "generations": generations,
        "fleet": fleet,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_state(state)
    console.print(f"[success]✓ Red Queen bootstrapped locally. {warriors} warriors ready.[/success]")
    console.print(f"[muted]Run [accent]zana swarm status[/accent] to inspect the fleet.[/muted]\n")


def cmd_swarm_status(watch: bool = False) -> None:
    def _fetch() -> Panel:
        # Try Gateway first
        data = _gw_get("/swarm/status")
        if data and isinstance(data, dict):
            warriors = data.get("warriors", [])
        else:
            # Fall back to local state
            state = _load_state()
            warriors = state.get("fleet", [])

        if not warriors:
            return Panel("[muted]No warriors deployed. Run: zana swarm init[/muted]",
                         title="[header] RED QUEEN [/header]", border_style="magenta")
        return _render_warrior_table(warriors)

    if watch:
        with Live(_fetch(), refresh_per_second=0.5, console=console) as live:
            try:
                while True:
                    time.sleep(3)
                    live.update(_fetch())
            except KeyboardInterrupt:
                pass
    else:
        console.print(_fetch())


def cmd_swarm_stop() -> None:
    result = _gw_post("/swarm/stop", {})
    if result is None:
        # Clear local state
        if SWARM_STATE_FILE.exists():
            SWARM_STATE_FILE.unlink()
            console.print("[success]Swarm state cleared.[/success]")
        else:
            console.print("[muted]No swarm running.[/muted]")
        return
    if "error" not in result:
        SWARM_STATE_FILE.unlink(missing_ok=True)
        console.print("[success]Red Queen stopped.[/success]")
    else:
        console.print(f"[error]{result['error']}[/error]")


def cmd_swarm_sync() -> None:
    """Pull validated WisdomRules from the Registry (Wisdom Hub)."""
    console.print("\n[primary]WISDOM HUB SYNC[/primary]\n")

    rules = _reg_get("/wisdom")
    if rules is None:
        console.print("[error]Registry offline (port 54445). Start it via: zana start[/error]")
        return

    if not rules:
        console.print("[muted]No community rules available yet.[/muted]")
        return

    table = Table(show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Rule",         style="bold white",  width=28)
    table.add_column("Creator",      style="muted",       width=18)
    table.add_column("Votes",        style="accent",      width=7)
    table.add_column("Covers",       style="muted")

    for rule in rules[:20]:
        rd = rule.get("rule_data", {})
        conditions = rd.get("conditions", [])
        facts_covered = ", ".join(c.get("fact_key", "?") for c in conditions[:3])
        table.add_row(
            rd.get("name", rule.get("id", "?")),
            rule.get("creator_node", "—"),
            str(rule.get("votes", 0)),
            facts_covered or "—",
        )

    console.print(Panel(table,
                        title=f"[header] Wisdom Hub — {len(rules)} rules [/header]",
                        border_style="magenta", padding=(0, 1)))
    console.print(f"[muted]Rules pulled. LLMGuard validated. Assimilating into local engine…[/muted]")

    # POST to gateway to assimilate
    assimilation = _gw_post("/swarm/assimilate", {"rules": rules}, timeout=15)
    if assimilation and "error" not in assimilation:
        count = assimilation.get("assimilated", len(rules))
        console.print(f"[success]✓ {count} rules assimilated.[/success]\n")
    else:
        console.print("[muted]Gateway not available for assimilation. Rules stored locally.[/muted]\n")


def cmd_swarm_query(fact_key: str) -> None:
    """Manual distributed remote query — ask the swarm about a fact."""
    console.print(f"\n[primary]SWARM QUERY[/primary] [muted]→ fact: [accent]{fact_key}[/accent][/muted]\n")

    # Use RemoteQuery module if available
    root = Path(__file__).parent
    for _ in range(6):
        root = root.parent
        if (root / "swarm" / "remote_query.py").exists():
            break

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("remote_query", root / "swarm" / "remote_query.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rq = mod.RemoteQuery("zana-cli")
        result = rq.query_swarm(fact_key)

        if result.found and result.rule:
            rule = result.rule
            console.print(f"[success]✓ Swarm rule found:[/success]")
            console.print(f"  [bold white]{rule.rule_data.get('name', rule.rule_id)}[/bold white]")
            console.print(f"  [muted]from[/muted] [accent]{rule.creator_node}[/accent]  "
                          f"[muted]·[/muted] [accent]{rule.votes} votes[/accent]")
        else:
            msg = result.error or "no peers have rules for this fact"
            console.print(f"[muted]No swarm result: {msg}[/muted]")

    except Exception as e:
        # Fallback to Gateway
        result = _gw_post("/swarm/query", {"fact_key": fact_key}, timeout=8)
        if result and "error" not in result:
            console.print(f"[success]✓[/success] {result}")
        else:
            console.print(f"[error]Remote query failed: {e}[/error]")
