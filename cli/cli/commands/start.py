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

    # 2. Ensure Rust Steel Core is built (needed for Docker build context)
    _ensure_steel_core_built(STACK_ROOT)

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
                console.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
                console.print("[success]  Córtex en línea. El Gateway está activo.[/success]")
                console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
                console.print("\n[bold white]🌐 Abre tu navegador en:[/bold white] [bold cyan]http://localhost[/bold cyan] [muted](o la IP/dominio de tu VPS)[/muted]")
                console.print("[muted]Inicia el Ritual de Resonancia e interactúa con tu Aeón.[/muted]\n")
                return
        except Exception:
            pass
        console.print("[muted].[/muted]", end="")
        time.sleep(2)

    console.print()
    console.print(
        "[warning]Gateway did not respond in time. Run `zana status` to check.[/warning]"
    )


def _ensure_steel_core_built(root: Path) -> None:
    """Ensures that the .so files (The Steel Core) exist in the root."""
    needed = ["zana_steel_core.so", "zana_audio_dsp.so", "zana_armor.so"]
    
    console.print(f"[muted]Checking Steel Core in: {root}[/muted]")
    
    missing = []
    for f in needed:
        if not (root / f).exists():
            missing.append(f)
        else:
            # Check if it is a regular file and not empty
            if not (root / f).is_file() or (root / f).stat().st_size == 0:
                missing.append(f)

    if not missing:
        console.print("[success]✓ Steel Core components found.[/success]")
        return

    console.print(f"[warning]Missing or invalid Steel Core components: {', '.join(missing)}.[/warning]")
    console.print("[primary]Forging The Steel Core (Rust)...[/primary]")
    
    try:
        # 1. Build Steel Core (Rust)
        rust_dir = root / "rust_core"
        if rust_dir.exists():
            console.print("[muted]  -> Forging Steel Core (PyO3)...[/muted]")
            subprocess.run(["cargo", "build", "--release", "--features", "python"], cwd=str(rust_dir), check=True)
            subprocess.run(["cp", "target/release/libzana_steel_core.so", str(root / "zana_steel_core.so")], cwd=str(rust_dir), check=True)
        else:
            console.print(f"[error]Error: {rust_dir} not found. Cannot build zana_steel_core.so[/error]")

        # 2. Build Audio DSP
        audio_dir = root / "audio_dsp"
        if audio_dir.exists():
            console.print("[muted]  -> Forging Audio DSP (VAD)...[/muted]")
            subprocess.run(["cargo", "build", "--release"], cwd=str(audio_dir), check=True)
            subprocess.run(["cp", "target/release/libzana_audio_dsp.so", str(root / "zana_audio_dsp.so")], cwd=str(audio_dir), check=True)
        else:
             console.print(f"[error]Error: {audio_dir} not found. Cannot build zana_audio_dsp.so[/error]")

        # 3. Build Armor
        armor_dir = root / "armor"
        if armor_dir.exists():
            console.print("[muted]  -> Forging Armor (Security)...[/muted]")
            subprocess.run(["cargo", "build", "--release"], cwd=str(armor_dir), check=True)
            subprocess.run(["cp", "target/release/libzana_armor.so", str(root / "zana_armor.so")], cwd=str(armor_dir), check=True)
        else:
             console.print(f"[error]Error: {armor_dir} not found. Cannot build zana_armor.so[/error]")

        console.print("[success]The Steel Core has been forged successfully.[/success]")
    except Exception as e:
        console.print(f"[error]Failed to forge The Steel Core: {e}[/error]")
        console.print("[muted]Try building manually: cd rust_core && cargo build --release[/muted]")
        raise typer.Exit(1)
