import subprocess
import sys
from pathlib import Path

import typer

from cli.tui.theme import console

EMBEDDER_DIR = Path(__file__).parent.parent.parent.parent / "embedder"


def cmd_embed(vault_path: str | None = None, reset: bool = False) -> None:
    if not EMBEDDER_DIR.exists():
        console.print(f"[error]Embedder module not found at {EMBEDDER_DIR}[/error]")
        raise typer.Exit(1)

    args = [sys.executable, "-m", "embedder.main"]
    if reset:
        args.append("--reset")
    if vault_path:
        args += ["--vault", vault_path]

    console.print("[primary]Starting vault embedding...[/primary]")
    result = subprocess.run(args, cwd=str(EMBEDDER_DIR.parent))

    if result.returncode != 0:
        raise typer.Exit(result.returncode)
