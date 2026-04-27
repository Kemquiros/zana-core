import os
import subprocess
from pathlib import Path

import typer

from cli.tui.theme import console

# Smart STACK_ROOT resolution
def _resolve_stack_root() -> Path:
    # 1. Check environment variable
    env_root = os.getenv("ZANA_CORE_DIR")
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    # 2. Check for repo clone (dev mode)
    dev_root = Path(__file__).parent.parent.parent.parent
    if (dev_root / "docker-compose.yml").exists():
        return dev_root
        
    # 3. Check for standard install location
    install_root = Path.home() / ".zana" / "core-repo"
    if (install_root / "docker-compose.yml").exists():
        return install_root
        
    return dev_root # Fallback to dev_root for error reporting

STACK_ROOT = _resolve_stack_root()

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
