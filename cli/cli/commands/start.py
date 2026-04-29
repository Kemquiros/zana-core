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

    # 2. Fix data directory permissions (Docker context scan fix)
    _fix_data_permissions(STACK_ROOT)

    # 3. Ensure Rust Steel Core is built (needed for Docker build context)
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


def _fix_data_permissions(root: Path) -> None:
    """Fixes permissions in the data directory to allow Docker context scanning."""
    data_dir = root / "data"
    if not data_dir.exists():
        return

    # Check if any subdirectory is unreadable
    try:
        # This will fail if we can't read/enter subfolders (like data/caddy/caddy)
        subprocess.run(["find", str(data_dir), "-maxdepth", "2"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        console.print("\n[bold yellow]🔐 CORRIGIENDO PERMISOS DE DATOS...[/bold yellow]")
        console.print("[muted]Docker requiere acceso de lectura para ignorar carpetas protegidas.[/muted]")
        try:
            # Try to add read and directory-search permissions
            # Using sudo might be needed if files are root-owned by Docker
            cmd = ["sudo", "chmod", "-R", "a+rX", str(data_dir)]
            subprocess.run(cmd, check=True)
            console.print("[success]✅ Permisos restaurados.[/success]")
        except Exception:
            console.print("[error]No se pudieron corregir los permisos automáticamente.[/error]")
            console.print(f"[yellow]Ejecuta manualmente: sudo chmod -R a+rX {data_dir}[/yellow]")


def _ensure_rust_installed() -> str:
    """Return path to cargo, installing Rust via rustup if needed."""
    import shutil

    cargo = shutil.which("cargo")
    if cargo:
        return cargo

    # cargo might exist in ~/.cargo/bin even if not on PATH yet
    cargo_home = Path.home() / ".cargo" / "bin" / "cargo"
    if cargo_home.exists():
        os.environ["PATH"] = f"{cargo_home.parent}:{os.environ.get('PATH', '')}"
        return str(cargo_home)

    console.print("\n[bold yellow]⚙️  Rust no detectado — instalando via rustup...[/bold yellow]")
    console.print("[muted]Esto toma 1-2 minutos y solo ocurre una vez.[/muted]")

    result = subprocess.run(
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path",
        shell=True,
    )
    if result.returncode != 0:
        console.print("[error]No se pudo instalar Rust automáticamente.[/error]")
        console.print("[yellow]Instálalo manualmente: https://rustup.rs  →  luego ejecuta `zana start` de nuevo.[/yellow]")
        raise typer.Exit(1)

    os.environ["PATH"] = f"{cargo_home.parent}:{os.environ.get('PATH', '')}"
    console.print("[success]✅ Rust instalado correctamente.[/success]\n")
    return str(cargo_home)


def _ensure_steel_core_built(root: Path) -> None:
    """Ensures that the .so files (The Steel Core) exist in the root."""
    needed = ["zana_steel_core.so", "zana_audio_dsp.so", "zana_armor.so"]

    console.print(f"\n[bold cyan]🔍 VERIFICANDO THE STEEL CORE...[/bold cyan]")
    console.print(f"[muted]Directorio base: {root}[/muted]")

    missing = []
    for f in needed:
        f_path = root / f
        if not f_path.exists() or not f_path.is_file() or f_path.stat().st_size == 0:
            missing.append(f)

    if not missing:
        console.print("[bold green]✅ Todos los componentes binarios están presentes y validados.[/bold green]\n")
        return

    console.print(f"[bold yellow]⚠️  Componentes faltantes o inválidos: {', '.join(missing)}[/bold yellow]")
    console.print("[bold magenta]⚙️  INICIANDO PROCESO DE FORJA (Rust + PyO3)...[/bold magenta]")

    cargo = _ensure_rust_installed()

    try:
        # 1. Build Steel Core (Rust)
        if "zana_steel_core.so" in missing:
            rust_dir = root / "rust_core"
            if not rust_dir.exists():
                console.print(f"[error]Error fatal: Directorio {rust_dir} no encontrado.[/error]")
                raise typer.Exit(1)
            console.print("[cyan]  ▶ Forjando Steel Core (Cognición)...[/cyan]")
            subprocess.run([cargo, "build", "--release", "--features", "python"], cwd=str(rust_dir), check=True)
            subprocess.run(["cp", "target/release/libzana_steel_core.so", str(root / "zana_steel_core.so")], cwd=str(rust_dir), check=True)

        # 2. Build Audio DSP
        if "zana_audio_dsp.so" in missing:
            audio_dir = root / "audio_dsp"
            if audio_dir.exists():
                console.print("[cyan]  ▶ Forjando Audio DSP (Sexto Sentido)...[/cyan]")
                subprocess.run([cargo, "build", "--release"], cwd=str(audio_dir), check=True)
                subprocess.run(["cp", "target/release/libzana_audio_dsp.so", str(root / "zana_audio_dsp.so")], cwd=str(audio_dir), check=True)

        # 3. Build Armor
        if "zana_armor.so" in missing:
            armor_dir = root / "armor"
            if armor_dir.exists():
                console.print("[cyan]  ▶ Forjando Armor Layer (Soberanía)...[/cyan]")
                subprocess.run([cargo, "build", "--release"], cwd=str(armor_dir), check=True)
                subprocess.run(["cp", "target/release/libzana_armor.so", str(root / "zana_armor.so")], cwd=str(armor_dir), check=True)

        console.print("[bold green]✨ The Steel Core ha sido forjado con éxito para tu arquitectura.[/bold green]\n")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]❌ Error durante la forja:[/bold red] {e}")
        console.print("[yellow]Sugerencia: Ejecuta `cd rust_core && cargo build --release` manualmente.[/yellow]")
        raise typer.Exit(1)
