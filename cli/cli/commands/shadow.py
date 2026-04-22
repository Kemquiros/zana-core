"""
zana shadow — Shadow Observer daemon control.

The Shadow Observer runs as a background process, silently monitoring
all ZANA interactions and system events. It feeds the reward engine
for meta-evolutionary optimization without interrupting the main flow.

  zana shadow enable    start daemon
  zana shadow disable   stop daemon
  zana shadow status    show daemon health
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from rich.panel import Panel
from rich.table import Table
from rich import box

from cli.tui.theme import console

SHADOW_PID_FILE = Path.home() / ".config" / "zana" / "shadow.pid"
SHADOW_LOG_FILE = Path.home() / ".config" / "zana" / "shadow.log"
GATEWAY_URL = f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}"


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_pid() -> int | None:
    if SHADOW_PID_FILE.exists():
        try:
            return int(SHADOW_PID_FILE.read_text().strip())
        except Exception:
            return None
    return None


def cmd_shadow_enable() -> None:
    pid = _read_pid()
    if pid and _is_running(pid):
        console.print(
            f"[warning]Shadow Observer already running (PID {pid}).[/warning]"
        )
        return

    # Find shadow_observer entry point
    Path(
        __file__
    ).parent.parent.parent.parent.parent / "shadow_observer" / "src" / "main.rs"
    shadow_py = (
        Path(__file__).parent.parent.parent.parent.parent
        / "shadow_observer"
        / "shadow_daemon.py"
    )

    # Prefer a Python daemon shim; fall back to the Gateway's shadow endpoint
    if shadow_py.exists():
        proc = subprocess.Popen(
            [sys.executable, str(shadow_py)],
            stdout=open(SHADOW_LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        SHADOW_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        SHADOW_PID_FILE.write_text(str(proc.pid))
        console.print(f"[success]Shadow Observer started (PID {proc.pid}).[/success]")
        console.print(f"[muted]Logs: {SHADOW_LOG_FILE}[/muted]")
        return

    # Activate via Gateway signal
    try:
        r = httpx.post(f"{GATEWAY_URL}/shadow/enable", timeout=5)
        if r.status_code == 200:
            console.print("[success]Shadow Observer activated via Gateway.[/success]")
        else:
            console.print(f"[error]Gateway returned {r.status_code}[/error]")
    except Exception:
        console.print(
            "[error]Gateway offline. Start the stack first: zana start[/error]"
        )


def cmd_shadow_disable() -> None:
    pid = _read_pid()
    if pid and _is_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if _is_running(pid):
                os.kill(pid, signal.SIGKILL)
            SHADOW_PID_FILE.unlink(missing_ok=True)
            console.print(f"[success]Shadow Observer stopped (PID {pid}).[/success]")
            return
        except Exception as e:
            console.print(f"[error]Could not stop process: {e}[/error]")
            return

    # Deactivate via Gateway
    try:
        r = httpx.post(f"{GATEWAY_URL}/shadow/disable", timeout=5)
        if r.status_code == 200:
            console.print("[success]Shadow Observer deactivated via Gateway.[/success]")
        else:
            console.print("[muted]Shadow Observer was not running.[/muted]")
    except Exception:
        console.print("[muted]Shadow Observer not running.[/muted]")


def cmd_shadow_status() -> None:
    console.print("\n[primary]SHADOW OBSERVER[/primary]\n")

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("", style="bold white", width=20)
    table.add_column("", width=30)
    table.add_column("", style="muted")

    pid = _read_pid()
    if pid and _is_running(pid):
        table.add_row("Daemon PID", f"[success]{pid}[/success]", "local process")
        table.add_row("Log", str(SHADOW_LOG_FILE), "tail -f to watch")
    else:
        # Check via Gateway
        try:
            r = httpx.get(f"{GATEWAY_URL}/shadow/status", timeout=3)
            data = r.json() if r.status_code == 200 else {}
            active = data.get("active", False)
            table.add_row(
                "Daemon",
                (
                    "[success]✓ Active[/success]"
                    if active
                    else "[muted]— Inactive[/muted]"
                ),
                "via Gateway",
            )
            if active:
                table.add_row(
                    "Events captured", str(data.get("events_captured", "?")), ""
                )
                table.add_row("Last event", data.get("last_event", "—"), "")
        except Exception:
            table.add_row(
                "Daemon", "[muted]— Inactive[/muted]", "run: zana shadow enable"
            )

    console.print(
        Panel(
            table,
            title="[header] Shadow Observer Status [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
