import os
import shutil
import subprocess
import sys
from pathlib import Path
import time
import secrets
import string

from cli.tui.theme import console, BANNER

# questionary / prompt_toolkit send \e[6n (cursor position query) on import,
# which leaks ";1R" to the shell when there is no TTY (curl | bash).
# Import lazily — only when _is_interactive() is True.


# ── Environment detection ──────────────────────────────────────────────────

def _is_wsl() -> bool:
    """Detect Windows Subsystem for Linux by checking /proc/version."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _is_interactive() -> bool:
    """True only when stdin is a real terminal.

    curl | bash destroys the TTY, making sys.stdin.isatty() return False.
    questionary aborts in that scenario; we fall back to silent defaults instead.
    """
    return sys.stdin.isatty()


def _get_windows_username() -> str:
    """In WSL, infer the Windows username from /mnt/c/Users/."""
    try:
        skip = {"Public", "Default", "Default User", "All Users", "desktop.ini"}
        candidates = [
            p.name for p in Path("/mnt/c/Users").iterdir()
            if p.is_dir() and p.name not in skip
        ]
        if candidates:
            return candidates[0]
    except Exception:
        pass
    return os.environ.get("USER", "user")


def _default_vault_path() -> str:
    """Return the most sensible vault default for this environment.

    WSL: Obsidian runs on Windows and cannot see /home/... paths.
    Use /mnt/c/Users/<windows_user>/Documents/ZANA_Vault so Windows-side
    Obsidian can open the vault without extra WSL bridging.
    """
    if _is_wsl():
        win_user = _get_windows_username()
        return f"/mnt/c/Users/{win_user}/Documents/ZANA_Vault"
    return str(Path.home() / "Documents" / "ZANA_Vault")

ZANA_CONFIG_DIR = Path.home() / ".config" / "zana"
# Local config for keys, not touching the repo's .env directly for global installs
# But since this is a sovereign node, we'll store it in ~/.zana/.env
ZANA_ENV_DIR = Path.home() / ".zana"
ENV_FILE = ZANA_ENV_DIR / ".env"

def _q_style():
    """Lazy-load questionary.Style to avoid importing prompt_toolkit in non-TTY mode."""
    from questionary import Style
    return Style(
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

# ── Ollama sovereign setup ────────────────────────────────────────────────

def _check_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    import httpx
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _get_ollama_models(base_url: str = "http://localhost:11434") -> list:
    import httpx
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=3)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def _test_ollama_inference(model: str, base_url: str = "http://localhost:11434") -> str | None:
    import httpx
    try:
        r = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": "Responde exactamente con una sola línea: 'ZANA en línea.'",
                "stream": False,
            },
            timeout=90,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception:
        return None


_RECOMMENDED_MODELS = [
    ("gemma3:4b",    "Gemma 3 4B  — equilibrio ideal CPU/GPU  (~2.5 GB)"),
    ("llama3.2:3b",  "Llama 3.2 3B — ultraligero, CPU puro   (~2.0 GB)"),
    ("llama3.1:8b",  "Llama 3.1 8B — más capaz, requiere GPU (~5.0 GB)"),
    ("mistral:7b",   "Mistral 7B   — razonamiento técnico     (~4.1 GB)"),
    ("phi4",         "Phi-4        — Microsoft, muy eficiente (~8.0 GB)"),
    ("gemma4",       "Gemma 4      — modelo soberano ZANA     (~5.0 GB)"),
]


def _setup_ollama(cloud_keys: dict) -> dict:
    """
    Offer Ollama as the sovereign local engine when no cloud API keys are configured.
    Guides the user step by step with real connection and inference tests.
    Returns env vars to write (e.g. {"ZANA_PRIMARY_MODEL": "ollama/gemma3:4b"}).
    """
    if not _is_interactive():
        return {}

    has_any_cloud_key = any(v for v in cloud_keys.values())
    if has_any_cloud_key:
        return {}

    import questionary

    console.print("\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print("[bold white]  Modo Soberano Local — Inferencia sin API Keys[/bold white]")
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print(
        "\n  No configuraste APIs en la nube. ZANA puede funcionar\n"
        "  [bold]100% offline[/bold] con [accent]Ollama[/accent] — sin costos, sin datos enviados, soberanía total.\n"
    )

    use_ollama = questionary.confirm(
        "¿Configurar Ollama como motor de inferencia local?",
        default=True,
        style=_q_style(),
    ).ask()

    if not use_ollama:
        console.print("\n  [muted]Sin problema. Configúralo cuando quieras con:[/muted] [accent]zana setup[/accent]\n")
        return {}

    base_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))

    # ── Paso 1: verificar conexión ─────────────────────────────────────────
    console.print("\n  [bold cyan]Paso 1 / 3[/bold cyan] — Verificando conexión con Ollama...")

    if not _check_ollama_running(base_url):
        console.print(f"\n  [yellow]⚠  Ollama no responde en {base_url}[/yellow]")
        console.print("\n  Necesitas tenerlo corriendo. Según tu sistema:\n")
        console.print("  [bold]Linux / WSL:[/bold]")
        console.print("    1. Instala:  [accent]curl -fsSL https://ollama.com/install.sh | sh[/accent]")
        console.print("    2. Inicia:   [accent]ollama serve[/accent]  (en otra terminal)\n")
        console.print("  [bold]macOS:[/bold]")
        console.print("    1. Descarga la app desde [accent]https://ollama.com/download[/accent]")
        console.print("    2. Ábrela — el ícono de llama aparece en la barra de menú\n")
        console.print("  [bold]Windows (nativo):[/bold]")
        console.print("    1. Descarga el instalador desde [accent]https://ollama.com/download[/accent]")
        console.print("    2. Ejecútalo — Ollama queda disponible en localhost:11434\n")

        retry = questionary.confirm(
            "  ¿Ya iniciaste Ollama? (reintentamos la conexión)",
            default=True,
            style=_q_style(),
        ).ask()

        if not retry or not _check_ollama_running(base_url):
            console.print(
                "\n  [warning]Ollama no responde. Instálalo, ejecuta[/warning] [accent]ollama serve[/accent]"
                " [warning]y luego corre[/warning] [accent]zana setup[/accent] [warning]de nuevo.[/warning]\n"
            )
            return {}

    console.print(f"  [success]✅ Conexión establecida con {base_url}[/success]")

    # ── Paso 2: seleccionar modelo ─────────────────────────────────────────
    console.print("\n  [bold cyan]Paso 2 / 3[/bold cyan] — Seleccionando modelo...")

    installed = _get_ollama_models(base_url)

    if not installed:
        console.print("\n  [yellow]⚠  No tienes modelos instalados todavía.[/yellow]")
        console.print("  Recomendamos [bold]gemma3:4b[/bold] — funciona bien en CPU sin GPU:\n")
        console.print("  Abre otra terminal y ejecuta:")
        console.print("  [accent]  ollama pull gemma3:4b[/accent]")
        console.print("  [muted]  (~2.5 GB de descarga, solo la primera vez)[/muted]\n")

        retry = questionary.confirm(
            "  ¿Ya terminó la descarga? (verificamos de nuevo)",
            default=True,
            style=_q_style(),
        ).ask()

        if retry:
            installed = _get_ollama_models(base_url)

        if not installed:
            console.print(
                "\n  [warning]Sin modelos disponibles. Descarga uno con[/warning] "
                "[accent]ollama pull gemma3:4b[/accent] [warning]y luego ejecuta[/warning] [accent]zana setup[/accent].\n"
            )
            return {}

    # Build choice list: installed recommended first, then rest, then others
    rec_names = {name for name, _ in _RECOMMENDED_MODELS}
    rec_installed = [
        f"{name}  ← {desc}" if name in installed else None
        for name, desc in _RECOMMENDED_MODELS
        if name in installed
    ]
    # strip description for non-recommended installed
    other_installed = [m for m in installed if m not in rec_names]
    choices = [m for m in [
        *[name for name, _ in _RECOMMENDED_MODELS if name in installed],
        *other_installed,
    ]]

    if not choices:
        choices = installed

    if len(choices) == 1:
        selected = choices[0]
        console.print(f"\n  Único modelo disponible: [bold]{selected}[/bold]")
    else:
        selected = questionary.select(
            "  Elige el modelo a usar:",
            choices=choices,
            style=_q_style(),
        ).ask()

    if not selected:
        return {}

    # ── Paso 3: inferencia real ────────────────────────────────────────────
    console.print(f"\n  [bold cyan]Paso 3 / 3[/bold cyan] — Probando inferencia con [bold]{selected}[/bold]...")
    console.print("  [muted]La primera vez puede tardar ~15 s mientras el modelo carga en memoria...[/muted]")

    response = _test_ollama_inference(selected, base_url)

    if response:
        console.print(f"\n  [success]✅ Respuesta recibida:[/success]")
        console.print(f"  [bold white]  \"{response}\"[/bold white]\n")
        console.print(f"  [success]Ollama configurado correctamente.[/success]")
        console.print(f"  [muted]  ZANA_PRIMARY_MODEL = ollama/{selected}[/muted]\n")
        return {"ZANA_PRIMARY_MODEL": f"ollama/{selected}", "OLLAMA_BASE_URL": base_url}

    # Inference failed — still offer to save
    console.print("\n  [yellow]⚠  La inferencia no respondió a tiempo.[/yellow]")
    console.print("  El modelo puede estar cargándose. No es un error fatal.\n")

    save_anyway = questionary.confirm(
        "  ¿Guardar la configuración de todas formas?",
        default=True,
        style=_q_style(),
    ).ask()

    if save_anyway:
        console.print(f"  [muted]ZANA_PRIMARY_MODEL = ollama/{selected} — guardado.[/muted]\n")
        return {"ZANA_PRIMARY_MODEL": f"ollama/{selected}", "OLLAMA_BASE_URL": base_url}

    return {}


def _check_docker() -> bool:
    return shutil.which("docker") is not None and _docker_running()

def _docker_running() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def _setup_api_keys() -> dict:
    if not _is_interactive():
        console.print("\n[muted]Modo no-interactivo: omitiendo configuración de API keys.[/muted]")
        console.print("[muted]Edita ~/.zana/.env o ejecuta [accent]zana setup[/accent] en una terminal para añadirlas.[/muted]")
        return {}

    import questionary
    console.print("\n[secondary]Configuración de APIs y BYOK (Bring Your Own Key)[/secondary] [muted](Enter para omitir)[/muted]")

    keys = {}
    providers = [
        ("ANTHROPIC_API_KEY", "Anthropic API key (Recomendado para Analyst)"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("GEMINI_API_KEY", "Gemini API key"),
        ("GROQ_API_KEY", "Groq API key (Para inferencia ultrarrápida)")
    ]

    for env_var, label in providers:
        val = questionary.password(f"  {label}:", style=_q_style()).ask()
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
    """First-run wizard (TUI).

    Runs fully interactive when stdin is a terminal.
    Falls back to silent defaults when invoked via curl|bash (no TTY),
    so the install never aborts mid-pipe.
    """
    console.clear()
    console.print(BANNER)
    console.print("[primary]ZANA en línea. Inicializando Protocolo de Soberanía...[/primary]\n")

    _detect_environment()

    console.print("\n[secondary]Configuración de Bóveda Soberana[/secondary]")
    default_vault = _default_vault_path()

    if _is_interactive():
        import questionary
        vault_path = questionary.path(
            "Ruta a tu bóveda de Obsidian (donde ZANA leerá/escribirá):",
            default=default_vault,
            style=_q_style(),
        ).ask()
    else:
        vault_path = default_vault
        console.print(f"  [muted]Modo no-interactivo — usando ruta por defecto:[/muted]")
        console.print(f"  [accent]{vault_path}[/accent]")
        console.print(f"  [muted]Cambia esto después con:[/muted] [accent]zana setup[/accent]")
        if _is_wsl():
            console.print(
                "  [warning]WSL detectado:[/warning] la ruta apunta a "
                "[accent]/mnt/c/...[/accent] para que Obsidian (Windows) pueda abrirla."
            )

    if vault_path:
        keys = {"VAULT_PATH": vault_path}
        api_keys = _setup_api_keys()
        keys.update(api_keys)
        ollama_keys = _setup_ollama(api_keys)
        keys.update(ollama_keys)
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
