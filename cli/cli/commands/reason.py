"""
zana reason <fact> — trigger manual forward-chaining in the Rust reasoning engine.

Sends a structured fact to the Gateway /reason endpoint and displays
the deduction trace produced by the CLIPS-pattern engine.

Example:
  zana reason '{"fact_key": "machine_health_avg", "value": 0.3}'
  zana reason machine_health_avg=0.3
"""

import json
import os

import httpx
from rich.panel import Panel
from rich.tree import Tree
from rich import box
from rich.table import Table

from cli.tui.theme import console

GATEWAY_URL = f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}"


def _parse_fact(raw: str) -> dict:
    """
    Accept two formats:
      1. JSON string: '{"fact_key": "x", "value": 0.3}'
      2. key=value shorthand: machine_health_avg=0.3
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    if "=" in raw:
        key, _, val = raw.partition("=")
        try:
            parsed_val: float | bool | str = json.loads(val)
        except json.JSONDecodeError:
            parsed_val = val
        return {"fact_key": key.strip(), "value": parsed_val}

    # bare key — let the engine infer context
    return {"fact_key": raw}


def _render_trace(trace: list[dict]) -> None:
    tree = Tree("[primary]Forward-Chaining Trace[/primary]")
    for step in trace:
        rule_name = step.get("rule", "?")
        action = step.get("action", "")
        confidence = step.get("confidence")
        label = f"[accent]{rule_name}[/accent]"
        if confidence is not None:
            conf_color = (
                "success"
                if confidence >= 0.8
                else "warning" if confidence >= 0.5 else "error"
            )
            label += f"  [{conf_color}]{confidence:.2f}[/{conf_color}]"
        branch = tree.add(label)
        if action:
            branch.add(f"[muted]→ {action}[/muted]")
        for k, v in step.items():
            if k not in ("rule", "action", "confidence"):
                branch.add(f"[muted]{k}: {v}[/muted]")
    console.print(tree)


def cmd_reason(fact_raw: str, remote: bool = False) -> None:
    try:
        fact = _parse_fact(fact_raw)
    except ValueError as e:
        console.print(f"[error]Parse error: {e}[/error]")
        console.print(
            '[muted]Usage: zana reason \'fact_key=value\'  or  zana reason \'{"fact_key": "k", "value": 0}\'[/muted]'
        )
        return

    console.print(
        f"\n[primary]REASON[/primary] [muted]→ fact:[/muted] "
        f"[accent]{fact.get('fact_key', '?')}[/accent] "
        f"[muted]= {fact.get('value', '(no value)')}[/muted]"
        f"{'  [muted][+remote query][/muted]' if remote else ''}\n"
    )

    payload = {"fact": fact, "remote_query": remote}

    try:
        r = httpx.post(f"{GATEWAY_URL}/reason", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        console.print(
            f"[error]Gateway error {e.response.status_code}: {e.response.text[:200]}[/error]"
        )
        return
    except httpx.ConnectError:
        console.print("[error]Gateway offline. Run: zana start[/error]")
        return
    except Exception as e:
        console.print(f"[error]{e}[/error]")
        return

    # ── Deductions ───────────────────────────────────────────────────────────
    deductions = data.get("deductions", [])
    if deductions:
        table = Table(
            show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1)
        )
        table.add_column("Deduction", style="bold white")
        table.add_column("Confidence", width=10)
        table.add_column("Action", style="muted")
        for d in deductions:
            conf = d.get("confidence", 0)
            conf_color = (
                "success" if conf >= 0.8 else "warning" if conf >= 0.5 else "error"
            )
            table.add_row(
                d.get("conclusion", "—"),
                f"[{conf_color}]{conf:.2f}[/{conf_color}]",
                d.get("action", "—"),
            )
        console.print(
            Panel(
                table,
                title="[header] Deductions [/header]",
                border_style="magenta",
                padding=(0, 1),
            )
        )
    else:
        console.print("[muted]No deductions produced for this fact.[/muted]")

    # ── Trace ────────────────────────────────────────────────────────────────
    trace = data.get("trace", [])
    if trace:
        _render_trace(trace)

    # ── Remote query result ───────────────────────────────────────────────────
    swarm_rule = data.get("swarm_rule")
    if swarm_rule:
        console.print(
            f"\n[accent]Swarm contributed rule:[/accent] "
            f"[bold white]{swarm_rule.get('name', '?')}[/bold white] "
            f"[muted]from {swarm_rule.get('creator_node', '?')} "
            f"({swarm_rule.get('votes', 0)} votes)[/muted]"
        )
