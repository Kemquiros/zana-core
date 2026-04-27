import os
import subprocess
import time
from pathlib import Path

import httpx
import typer

from cli.tui.theme import console
from cli.tui.onboarding import ensure_env_configured

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
SERVICES = ["postgres", "redis", "neo4j", "zana-gateway", "aria-ui"]

def _get_gateway_url() -> str:
    # Use environment variable if set by dotenv, otherwise default to 54446
    port = os.getenv("ZANA_GATEWAY_PORT", "54446")
    return f"http://localhost:{port}/health"

def cmd_start(detach: bool = True) -> None:
    compose = STACK_ROOT / "docker-compose.yml"
    if not compose.exists():
        console.print(f"[error]docker-compose.yml not found at {STACK_ROOT}[/error]")
        raise typer.Exit(1)

    # 1. Ensure .env is securely configured with passwords before starting
    ensure_env_configured(STACK_ROOT)

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
    gateway_url = _get_gateway_url()

    while time.time() < deadline:
        try:
            r = httpx.get(gateway_url, timeout=2)
            if r.status_code == 200:
                console.print()
                console.print("[success]Gateway online.[/success]")
                return
        except Exception:
            pass
        console.print("[muted].[/muted]", end="")
        time.sleep(2)

    console.print()
    console.print(
        "[warning]Gateway did not respond in time. Run `zana status` to check.[/warning]"
    )
