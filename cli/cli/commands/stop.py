import subprocess
from pathlib import Path

import typer

from cli.tui.theme import console

STACK_ROOT = Path(__file__).parent.parent.parent.parent


def cmd_stop(volumes: bool = False) -> None:
    compose = STACK_ROOT / "docker-compose.yml"
    flags = ["-v"] if volumes else []

    console.print("[primary]Shutting down ZANA stack...[/primary]")
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose), "down"] + flags,
        cwd=str(STACK_ROOT),
    )

    if result.returncode == 0:
        console.print("[success]Stack offline.[/success]")
    else:
        console.print("[error]docker compose down failed.[/error]")
        raise typer.Exit(result.returncode)
