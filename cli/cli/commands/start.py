import subprocess
import time
from pathlib import Path

import httpx
import typer

from cli.tui.theme import console

STACK_ROOT = Path(__file__).parent.parent.parent.parent
GATEWAY_URL = "http://localhost:54446/health"
SERVICES = ["chromadb", "postgres", "redis", "neo4j", "zana-gateway", "aria-ui"]


def cmd_start(detach: bool = True) -> None:
    compose = STACK_ROOT / "docker-compose.yml"
    if not compose.exists():
        console.print(f"[error]docker-compose.yml not found at {STACK_ROOT}[/error]")
        raise typer.Exit(1)

    console.print("[primary]Booting ZANA stack...[/primary]")

    flags = ["-d"] if detach else []
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose), "up", "--build"] + flags,
        cwd=str(STACK_ROOT),
    )

    if result.returncode != 0:
        console.print("[error]docker compose failed.[/error]")
        raise typer.Exit(result.returncode)

    if detach:
        _wait_for_gateway()


def _wait_for_gateway(timeout: int = 60) -> None:
    console.print("[muted]Waiting for Gateway...[/muted]", end="")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            r = httpx.get(GATEWAY_URL, timeout=2)
            if r.status_code == 200:
                console.print()
                console.print("[success]Gateway online.[/success]")
                return
        except Exception:
            pass
        console.print("[muted].[/muted]", end="")
        time.sleep(2)

    console.print()
    console.print("[warning]Gateway did not respond in time. Run `zana status` to check.[/warning]")
