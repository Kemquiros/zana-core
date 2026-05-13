"""
zana doctor — comprehensive system health audit.
Checks environment, dependencies, services, config, and Aeon state.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from zana.tui.theme import console

GATEWAY_PORT = int(os.getenv("ZANA_GATEWAY_PORT", "54446"))
CHROMA_PORT = int(os.getenv("ZANA_CHROMA_PORT", "58001"))
PG_PORT = int(os.getenv("ZANA_PG_PORT", "55433"))
REDIS_PORT = int(os.getenv("ZANA_REDIS_PORT", "56380"))
NEO4J_PORT = int(os.getenv("ZANA_NEO4J_PORT", "57474"))
ARIA_PORT = int(os.getenv("ZANA_PWA_PORT", "54448"))
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
REGISTRY_PORT = int(os.getenv("ZANA_REGISTRY_PORT", "54445"))


def _tcp(host: str, port: int) -> tuple[bool, float | None]:
    try:
        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=2):
            return True, round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        return False, None


def _http(url: str) -> tuple[bool, float | None]:
    try:
        t0 = time.perf_counter()
        r = httpx.get(url, timeout=2)
        return r.status_code < 500, round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        return False, None


def _cmd_version(cmd: list[str]) -> str | None:
    try:
        return (
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
            .strip()
            .splitlines()[0]
        )
    except Exception:
        return None


def _env_check() -> list[tuple[str, str, str]]:
    env_file = Path(".env")
    # ZANA is LLM-agnostic: any one provider is sufficient
    llm_providers = [
        ("ANTHROPIC_API_KEY", "Anthropic Claude"),
        ("OPENAI_API_KEY", "OpenAI GPT"),
        ("GEMINI_API_KEY", "Google Gemini"),
        ("GROQ_API_KEY", "Groq"),
        ("OLLAMA_BASE_URL", "Ollama (local)"),
    ]
    optional = ["GOOGLE_API_KEY", "ZANA_PRIMARY_MODEL", "VAULT_PATH"]
    rows = []
    if env_file.exists():
        rows.append((".env file", "[success]✓ Present[/success]", ""))
        content = env_file.read_text()

        # Check: at least one LLM provider configured
        active_providers = []
        for key, label in llm_providers:
            val = os.getenv(key, "")
            present = bool(val) or key in content
            if present:
                active_providers.append(label)
            rows.append(
                (
                    f"  {key}",
                    "[success]✓ Set[/success]"
                    if present
                    else "[muted]— not set[/muted]",
                    f"provider: {label}",
                )
            )

        if not active_providers:
            rows.insert(
                1,
                (
                    "  LLM Provider",
                    "[error]✗ None configured[/error]",
                    "zana init OR set any provider key → ZSM mode active",
                ),
            )
        else:
            rows.insert(
                1,
                (
                    "  LLM Provider",
                    f"[success]✓ {active_providers[0]}[/success]",
                    f"{len(active_providers)} provider(s) available",
                ),
            )

        for key in optional:
            val = os.getenv(key, "")
            present = bool(val) or key in content
            rows.append(
                (
                    f"  {key}",
                    "[success]✓ Set[/success]"
                    if present
                    else "[muted]— not set[/muted]",
                    "optional",
                )
            )
    else:
        rows.append((".env file", "[error]✗ Missing[/error]", "run: zana setup"))
    return rows


def cmd_doctor(fix: bool = False) -> None:
    console.print("\n[primary]ZANA DOCTOR[/primary] [muted]— System Audit[/muted]\n")

    # ── 1. Runtime Environment ────────────────────────────────────────────────
    env_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    env_table.add_column("", style="bold white", width=20)
    env_table.add_column("", width=32)
    env_table.add_column("", style="muted")

    py = _cmd_version([sys.executable, "--version"])
    node = _cmd_version(["node", "--version"]) if shutil.which("node") else None
    rust = _cmd_version(["rustc", "--version"]) if shutil.which("rustc") else None
    docker = _cmd_version(["docker", "--version"]) if shutil.which("docker") else None
    uv = _cmd_version(["uv", "--version"]) if shutil.which("uv") else None

    def _ok(v: str | None, min_label: str = "") -> str:
        if v:
            return f"[success]✓[/success] {v}"
        return "[error]✗ not found[/error]" + (
            f" (need {min_label})" if min_label else ""
        )

    env_table.add_row("Python", _ok(py, "3.12+"), "")
    env_table.add_row("Node.js", _ok(node, "22+"), "PWA build")
    env_table.add_row("Rust", _ok(rust, "stable"), "Armor / steel_core")
    env_table.add_row("Docker", _ok(docker), "Stack orchestration")
    env_table.add_row("uv", _ok(uv), "Package manager")

    # Docker running?
    if shutil.which("docker"):
        try:
            subprocess.check_output(
                ["docker", "info"], stderr=subprocess.DEVNULL, timeout=4
            )
            env_table.add_row("Docker daemon", "[success]✓ Running[/success]", "")
        except Exception:
            env_table.add_row(
                "Docker daemon",
                "[error]✗ Not running[/error]",
                "run: sudo systemctl start docker",
            )

    console.print(
        Panel(
            env_table,
            title="[header] Runtime Environment [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )

    # ── 2. Services ──────────────────────────────────────────────────────────
    svc_table = Table(
        show_header=True, header_style="header", box=box.SIMPLE, padding=(0, 1)
    )
    svc_table.add_column("Service", style="bold white", width=16)
    svc_table.add_column("Status", width=14)
    svc_table.add_column("Latency", width=10)
    svc_table.add_column("Role", style="muted")

    services = [
        (
            "Gateway",
            "http",
            f"http://localhost:{GATEWAY_PORT}/health",
            None,
            "Sensory + Armor",
        ),
        (
            "ChromaDB",
            "http",
            f"http://localhost:{CHROMA_PORT}/api/v1/heartbeat",
            None,
            "Semantic Memory",
        ),
        ("PostgreSQL", "tcp", "localhost", PG_PORT, "Episodic Memory"),
        ("Redis", "tcp", "localhost", REDIS_PORT, "Session Cache"),
        ("Neo4j", "http", f"http://localhost:{NEO4J_PORT}", None, "World Model"),
        ("ARIA UI", "http", f"http://localhost:{ARIA_PORT}", None, "PWA Interface"),
        (
            "Ollama",
            "http",
            f"http://localhost:{OLLAMA_PORT}/api/tags",
            None,
            "Local LLM (optional)",
        ),
        ("Registry", "tcp", "localhost", REGISTRY_PORT, "Swarm Registry"),
    ]

    online_count = 0
    weights = {
        "Gateway": 30,
        "ChromaDB": 20,
        "PostgreSQL": 15,
        "Redis": 10,
        "Neo4j": 15,
        "ARIA UI": 10,
    }

    for name, probe, target, port, role in services:
        if probe == "tcp":
            ok, lat = _tcp(target, port)
        else:
            ok, lat = _http(target)
        if ok:
            online_count += 1
        status_cell = (
            "[success]✓ Online[/success]"
            if ok
            else (
                "[muted]— Offline[/muted]"
                if name in ("Ollama", "Registry")
                else "[error]✗ Offline[/error]"
            )
        )
        lat_cell = f"{lat}ms" if lat else "—"
        svc_table.add_row(name, status_cell, lat_cell, role)

    zfi = sum(
        weights.get(n, 0)
        for n, *_ in services
        if _http(_[1] if _[0] == "http" else f"tcp://localhost:{_[2]}")[0]
        if False
    ) or sum(
        weights.get(name, 0)
        for name, probe, target, port, _ in services
        if (_http(target)[0] if probe == "http" else _tcp(target, port)[0])
    )
    zfi_color = "success" if zfi >= 90 else "warning" if zfi >= 60 else "error"
    console.print(
        Panel(
            svc_table,
            title="[header] Services [/header]",
            subtitle=f"  [{zfi_color}]ZFI {zfi}/100[/{zfi_color}]  ·  {online_count}/{len(services)} online",
            border_style="magenta",
            padding=(0, 1),
        )
    )

    # ── 3. Configuration ──────────────────────────────────────────────────────
    cfg_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    cfg_table.add_column("", style="bold white", width=26)
    cfg_table.add_column("", width=28)
    cfg_table.add_column("", style="muted")

    for row in _env_check():
        cfg_table.add_row(*row)

    session_file = Path.home() / ".config" / "zana" / "session.json"
    if session_file.exists():
        import json

        try:
            session = json.loads(session_file.read_text())
            active = session.get("active_aeon", "herald")
            cfg_table.add_row(
                "Active Aeon", f"[accent]{active}[/accent]", "zana aeon use <id>"
            )
        except Exception:
            cfg_table.add_row("Active Aeon", "[muted]— unreadable[/muted]", "")
    else:
        cfg_table.add_row("Active Aeon", "[muted]herald (default)[/muted]", "")

    console.print(
        Panel(
            cfg_table,
            title="[header] Configuration [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )

    # ── 4. Verdict ────────────────────────────────────────────────────────────
    if zfi >= 90:
        console.print("[success]✓ System is healthy. ZFI HOT.[/success]\n")
    elif zfi >= 60:
        console.print(
            "[warning]⚠ System partially operational. Start missing services with: zana start[/warning]\n"
        )
    else:
        console.print("[error]✗ Critical services offline. Run: zana start[/error]\n")

    if fix:
        issues = _collect_fixable_issues()
        if not issues:
            console.print("[success]✓ No se detectaron problemas reparables.[/success]")
        else:
            console.print(
                f"\n[warning]Se encontraron {len(issues)} problema(s) reparable(s):[/warning]"
            )
            _run_fixes(issues)
            console.print("\n[primary]Re-auditando tras los fixes...[/primary]\n")
            for row in _env_check():
                console.print(f"  {row[0]}  {row[1]}  [muted]{row[2]}[/muted]")


# ── Fix helpers ───────────────────────────────────────────────────────────────


def _upsert_env_var(key: str, value: str) -> None:
    """Read ~/.zana/.env, replace existing key or append, then write back."""
    env_file = Path.home() / ".zana" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    new_lines = [ln for ln in lines if not ln.startswith(f"{key}=")]
    new_lines.append(f'{key}="{value}"')
    env_file.write_text("\n".join(new_lines) + "\n")


def _collect_fixable_issues() -> list[dict]:
    """Inspect the environment and return a list of actionable issue dicts."""
    issues: list[dict] = []

    # --- no_llm_key: none of the known provider keys is set ------------------
    llm_keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OLLAMA_BASE_URL",
    ]
    zana_env = Path.home() / ".zana" / ".env"
    env_content = zana_env.read_text() if zana_env.exists() else ""
    has_llm = any(bool(os.getenv(k)) or k in env_content for k in llm_keys)
    if not has_llm:
        issues.append(
            {
                "id": "no_llm_key",
                "label": "No hay API key de LLM configurada",
                "fixable": True,
                "fix_hint": "",
            }
        )

    # --- no_vault_path -------------------------------------------------------
    vault_set = bool(os.getenv("VAULT_PATH")) or "VAULT_PATH" in env_content
    if not vault_set:
        issues.append(
            {
                "id": "no_vault_path",
                "label": "VAULT_PATH no configurado",
                "fixable": True,
                "fix_hint": "",
            }
        )

    # --- pipx_missing --------------------------------------------------------
    if not shutil.which("pipx"):
        issues.append(
            {
                "id": "pipx_missing",
                "label": "pipx no encontrado",
                "fixable": True,
                "fix_hint": "",
            }
        )

    # --- zana_outdated -------------------------------------------------------
    if shutil.which("pipx"):
        issues.append(
            {
                "id": "zana_outdated",
                "label": "vecanova-zana puede tener actualizaciones",
                "fixable": True,
                "fix_hint": "",
            }
        )

    # --- path_missing_local_bin ----------------------------------------------
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in os.environ.get("PATH", ""):
        issues.append(
            {
                "id": "path_missing_local_bin",
                "label": "~/.local/bin no está en PATH",
                "fixable": True,
                "fix_hint": "",
            }
        )

    # --- python_old ----------------------------------------------------------

    return issues


def _run_fixes(issues: list[dict]) -> None:
    """Iterate over detected issues and interactively fix each one."""
    import questionary

    for issue in issues:
        console.print(f"\n[warning]Problema:[/warning] {issue['label']}")

        if not issue["fixable"]:
            console.print(f"[muted]Instrucción: {issue['fix_hint']}[/muted]")
            continue

        if not typer.confirm("  ¿Intentar reparar automáticamente?", default=True):
            continue

        try:
            _apply_fix(issue["id"], questionary)
            console.print("[success]  ✓ Fix aplicado correctamente.[/success]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[error]  ✗ Fix fallido: {exc}[/error]")


def _apply_fix(issue_id: str, questionary) -> None:  # noqa: ANN001
    """Execute the automated repair for a single issue id."""
    provider_key_map = {
        "Anthropic (Claude)": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Google Gemini": "GEMINI_API_KEY",
        "Groq": "GROQ_API_KEY",
        "Ollama (local)": "OLLAMA_BASE_URL",
    }

    if issue_id == "no_llm_key":
        provider = questionary.select(
            "¿Qué proveedor LLM quieres configurar?",
            choices=list(provider_key_map.keys()),
        ).ask()
        if provider is None:
            raise RuntimeError("Operación cancelada por el usuario.")
        key_name = provider_key_map[provider]
        api_key = questionary.password("Ingresa tu API key:").ask()
        if not api_key:
            raise RuntimeError("API key vacía — operación cancelada.")
        _upsert_env_var(key_name, api_key)

    elif issue_id == "no_vault_path":
        path_str = questionary.text(
            "Ruta a tu vault (Obsidian o carpeta de notas):"
        ).ask()
        if not path_str:
            raise RuntimeError("Ruta vacía — operación cancelada.")
        vault_path = Path(path_str).expanduser()
        if not vault_path.exists():
            raise RuntimeError(f"El directorio no existe: {vault_path}")
        _upsert_env_var("VAULT_PATH", str(vault_path))

    elif issue_id == "pipx_missing":
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "pipx"], check=True
        )

    elif issue_id == "zana_outdated":
        pipx_bin = shutil.which("pipx")
        if pipx_bin:
            subprocess.run([pipx_bin, "upgrade", "vecanova-zana"], check=True)
        else:
            raise RuntimeError("pipx no encontrado — instálalo primero.")

    elif issue_id == "path_missing_local_bin":
        local_bin = str(Path.home() / ".local" / "bin")
        path_line = f'\nexport PATH="{local_bin}:$PATH"\n'
        for rc in ["~/.bashrc", "~/.zshrc", "~/.profile"]:
            rc_path = Path(rc).expanduser()
            if rc_path.exists() and local_bin not in rc_path.read_text():
                rc_path.write_text(rc_path.read_text() + path_line)
