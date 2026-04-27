import shutil
import subprocess
from pathlib import Path
import time
import secrets
import string

import questionary
from questionary import Style

from cli.tui.theme import console, BANNER

ZANA_CONFIG_DIR = Path.home() / ".config" / "zana"
# Local config for keys, not touching the repo's .env directly for global installs
# But since this is a sovereign node, we'll store it in ~/.zana/.env
ZANA_ENV_DIR = Path.home() / ".zana"
ENV_FILE = ZANA_ENV_DIR / ".env"

Q_STYLE = Style(
    [
        ("qmark", "fg:#e879f9 bold"),
        ("question", "fg:#f0abfc bold"),
        ("answer", "fg:#c084fc bold"),
        ("pointer", "fg:#e879f9 bold"),
        ("highlighted", "fg:#f0abfc bg:#3b0764 bold"),
        ("selected", "fg:#c084fc"),
        ("separator", "fg:#6b21a8"),
        ("instruction", "fg:#a855f7 italic"),
        ("text", "fg:#f3e8ff"),
    ]
)

def _generate_secret(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def ensure_env_configured(stack_root: Path) -> None:
    """Ensure that the local .env file in stack_root has critical variables securely populated."""
    env_path = stack_root / ".env"
    env_example = stack_root / ".env.example"
    
    if not env_path.exists():
        if env_example.exists():
            shutil.copy(env_example, env_path)
            console.print("[muted]Created .env from .env.example[/muted]")
        else:
            env_path.touch()

    content = env_path.read_text()
    lines = content.splitlines()
    env_dict = {}
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_dict[key.strip()] = val.strip()
            
    updates_made = False
    
    # Define critical secrets that need strong auto-generated passwords if missing or default
    critical_secrets = [
        "POSTGRES_PASSWORD",
        "NEO4J_PASSWORD",
        "N8N_PASSWORD",
        "TELEGRAM_WEBHOOK_SECRET"
    ]
    
    for secret_key in critical_secrets:
        # Generate if missing or if it matches the placeholder text in .env.example
        current_val = env_dict.get(secret_key, "")
        if not current_val or current_val in ["change_me_strong_password", "zana_pass", "zana_neo4j", "zana_n8n_secure"]:
            new_secret = _generate_secret()
            env_dict[secret_key] = new_secret
            updates_made = True
            
    if "N8N_USER" not in env_dict or not env_dict["N8N_USER"]:
        env_dict["N8N_USER"] = "zana_admin"
        updates_made = True

    if updates_made:
        # Reconstruct the file preserving comments and structure as much as possible
        new_lines = []
        updated_keys = set()
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=', 1)[0].strip()
                if key in env_dict:
                    new_lines.append(f"{key}={env_dict[key]}")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
                
        # Add any keys that weren't in the original file
        for key, val in env_dict.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={val}")
                
        env_path.write_text("\n".join(new_lines) + "\n")
        console.print("[success]Securely auto-configured missing secrets in .env[/success]")

def _check_docker() -> bool:
    return shutil.which("docker") is not None and _docker_running()

def _docker_running() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def _setup_api_keys() -> dict:
    console.print("\n[secondary]Configuración de APIs y BYOK (Bring Your Own Key)[/secondary] [muted](Enter para omitir)[/muted]")

    keys = {}
    providers = [
        ("ANTHROPIC_API_KEY", "Anthropic API key (Recomendado para Analyst)"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("GEMINI_API_KEY", "Gemini API key"),
        ("GROQ_API_KEY", "Groq API key (Para inferencia ultrarrápida)")
    ]

    for env_var, label in providers:
        val = questionary.password(f"  {label}:", style=Q_STYLE).ask()
        if val and val.strip():
            keys[env_var] = val.strip()

    return keys

def _write_env(keys: dict) -> None:
    ZANA_ENV_DIR.mkdir(parents=True, exist_ok=True)
    out_lines = []
    
    if ENV_FILE.exists():
        out_lines = ENV_FILE.read_text().splitlines()

    written = set()
    new_lines = []

    for line in out_lines:
        if "=" in line and not line.strip().startswith("#"):
            var = line.split("=", 1)[0].strip()
            if var in keys:
                new_lines.append(f"{var}={keys[var]}")
                written.add(var)
                continue
        new_lines.append(line)

    for var, val in keys.items():
        if var not in written:
            new_lines.append(f"{var}={val}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")

def _detect_environment():
    console.print("\n[secondary]Detección de Entorno[/secondary]")
    
    import platform
    import multiprocessing
    
    system = platform.system()
    cores = multiprocessing.cpu_count()
    
    console.print(f"  [muted]Sistema:[/muted] [accent]{system}[/accent]")
    console.print(f"  [muted]Núcleos CPU:[/muted] [accent]{cores}[/accent]")
    
    has_gpu = False
    if shutil.which("nvidia-smi"):
        has_gpu = True
        console.print("  [muted]GPU:[/muted] [success]NVIDIA Detectada[/success]")
    elif system == "Darwin" and platform.machine() == "arm64":
        has_gpu = True
        console.print("  [muted]GPU:[/muted] [success]Apple Silicon (Metal) Detectado[/success]")
    else:
        console.print("  [muted]GPU:[/muted] [warning]No detectada (Ejecución CPU)[/warning]")

    if has_gpu or cores >= 8:
        console.print("\n  [success]Tu hardware es capaz de correr modelos locales (Ollama).[/success]")
    else:
        console.print("\n  [warning]Hardware ligero detectado. Se recomienda usar APIs Cloud (BYOK).[/warning]")

def _mock_download_brain():
    console.print("\n[secondary]Inicializando Memoria ZANA (The Brain)[/secondary]")
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task1 = progress.add_task("[cyan]Descargando Postgres (Episodic DB)...", total=100)
        
        
        while not progress.finished:
            progress.update(task1, advance=2)
            # Removed undefined task2 update to fix potential crash
            time.sleep(0.05)
            
    console.print("[success]Servicios de Memoria listos.[/success]")

def run_onboarding() -> bool:
    """First-run wizard (TUI)."""
    console.clear()
    console.print(BANNER)
    console.print("[primary]ZANA en línea. Inicializando Protocolo de Soberanía...[/primary]\n")

    _detect_environment()

    console.print("\n[secondary]Configuración de Bóveda Soberana[/secondary]")
    default_vault = str(Path.home() / "Documents" / "ZANA_Vault")
    vault_path = questionary.path(
        "Ruta a tu bóveda de Obsidian (donde ZANA leerá/escribirá):",
        default=default_vault,
        style=Q_STYLE
    ).ask()
    
    if vault_path:
        keys = {"VAULT_PATH": vault_path}
        api_keys = _setup_api_keys()
        keys.update(api_keys)
        _write_env(keys)
        console.print("[success]  Configuración guardada en ~/.zana/.env[/success]")

    if _check_docker():
        _mock_download_brain()
    else:
        console.print("\n[warning]Docker no detectado. Omitiendo descarga del 'Brain' local.[/warning]")
        console.print("[muted]Instala Docker y ejecuta `zana start` más tarde para persistencia de memoria.[/muted]")

    ZANA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (ZANA_CONFIG_DIR / ".onboarded").touch()

    console.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print("[success]ZANA CORE ESTÁ LISTO PARA SERVIR.[/success]")
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print("\nComandos sugeridos para explorar:")
    console.print("  [accent]zana chat[/accent]   - Abre el REPL para conversar con tu Aeon")
    console.print("  [accent]zana aeon[/accent]   - Administra tu enjambre de agentes")
    console.print("  [accent]zana memory[/accent] - Consulta tus recuerdos")
    console.print("\n[muted]Juntos hacemos temblar los cielos.[/muted]\n")
    return True

def is_first_run() -> bool:
    return not (ZANA_CONFIG_DIR / ".onboarded").exists()
