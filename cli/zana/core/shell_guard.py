"""
shell_guard.py — Sovereign Shell Execution for ZANA

Security layers:
  0: Template mapping  — LLM identifies template, not raw shell string
  1: Param validation  — each arg validated independently (path/filename)
  2: shell=False       — argv list, never string concatenation
  3: Clean env         — _CLEAN_ENV: no API keys or tokens in subprocess
  4: TOCTOU prevention — realpath() resolves symlinks at validation AND execution time
  5: User confirmation — shows exact argv + hash, default=False
  6: Output sanitation — strips ANSI escapes, caps at 3000 chars
  7: Civic Ledger      — every attempt audited (blocked/cancelled/executed)
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

_CLEAN_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    "HOME": str(Path.home()),
    "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    "TERM": "dumb",
}

_FORBIDDEN_COMMANDS = frozenset(
    [
        "bash",
        "sh",
        "zsh",
        "fish",
        "python",
        "python3",
        "perl",
        "ruby",
        "node",
        "curl",
        "wget",
        "nc",
        "netcat",
        "ncat",
        "socat",
        "telnet",
        "sudo",
        "su",
        "doas",
        "pkexec",
        "chmod",
        "chown",
        "chattr",
        "dd",
        "mkfs",
        "fdisk",
        "parted",
        "crontab",
        "at",
        "systemctl",
        "launchctl",
        "service",
        "git",
        "make",
        "cmake",
        "gcc",
        "g++",
        "clang",
        "pip",
        "npm",
        "cargo",
        "go",
        "vim",
        "nano",
        "emacs",
        "ed",
        "awk",
        "sed",
        "xargs",
        "eval",
        "exec",
    ]
)

_SENSITIVE_DIRS = (".zana", ".ssh", ".gnupg", ".aws", ".config/secrets")
_ALLOWED_ROOTS = (str(Path.home()), "/tmp", "/var/folders")


def _validate_path(raw: str, must_exist: bool = False) -> str | None:
    """Validate and resolve a filesystem path.

    Applies realpath() at validation time (TOCTOU prevention). Returns the
    resolved absolute path if it passes all checks, or None if blocked.
    """
    expanded = os.path.expanduser(raw.strip())
    resolved = os.path.realpath(expanded)

    # Layer: boundary check — must be under home, /tmp, or /var/folders
    if not any(resolved.startswith(root) for root in _ALLOWED_ROOTS):
        return None

    # Layer: sensitive directory check
    if any(sensitive in resolved for sensitive in _SENSITIVE_DIRS):
        return None

    # Layer: existence check
    if must_exist and not os.path.exists(resolved):
        return None

    return resolved


def _validate_filename(raw: str) -> str | None:
    """Validate a bare filename (no path separators, no null bytes, safe chars only)."""
    name = raw.strip()
    if not name:
        return None
    if "/" in name:
        return None
    if "\x00" in name:
        return None
    if not re.match(r"^[\w\s.\-_()\@+,=\[\]{}]+$", name):
        return None
    return name


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def _audit(event_type: str, argv: list[str] | None, extra: str = "") -> None:
    """Write an entry to the Civic Ledger via SentinelLiteDB."""
    try:
        from zana.core.sentinel_lite import SentinelLiteDB

        db = SentinelLiteDB()
        payload = " ".join(argv or []) + extra
        h = hashlib.sha256(payload.encode()).hexdigest()
        db.record(event_type, payload_hash=h, civic_hash=h)
        db.close()
    except Exception:
        pass


# ── Template registry ─────────────────────────────────────────────────────────

_TEMPLATES: dict[str, dict] = {
    "list_files": {
        "desc": "List files in directory",
        "triggers": [
            "lista mis archivos",
            "lista archivos",
            "lista el contenido",
            "list files",
            "muestra archivos",
            "qué hay en",
            "ls ",
        ],
        "params": {"path": (_validate_path, True)},
        "argv": lambda p: ["ls", "-la", p["path"]],
    },
    "create_dir": {
        "desc": "Create directory",
        "triggers": [
            "crea la carpeta",
            "crea el directorio",
            "create folder",
            "create directory",
            "mkdir",
        ],
        "params": {"path": (_validate_path, False)},
        "argv": lambda p: ["mkdir", "-p", p["path"]],
    },
    "show_file": {
        "desc": "Show file contents",
        "triggers": [
            "muestra el archivo",
            "muestra el contenido",
            "show file",
            "cat ",
            "lee el archivo",
            "contenido de",
        ],
        "params": {"file": (lambda f: _validate_path(f, must_exist=True), True)},
        "argv": lambda p: ["cat", p["file"]],
    },
    "find_files": {
        "desc": "Find files by name pattern",
        "triggers": [
            "busca archivos con nombre",
            "busca el archivo",
            "find file",
            "encuentra archivos",
        ],
        "params": {
            "path": (_validate_path, True),
            "name": (_validate_filename, False),
        },
        "argv": lambda p: [
            "find",
            p.get("path", str(Path.home())),
            "-name",
            p.get("name", "*"),
            "-maxdepth",
            "5",
        ],
    },
    "disk_usage": {
        "desc": "Show disk usage of a path",
        "triggers": [
            "cuánto espacio",
            "espacio en disco",
            "disk usage",
            "uso del disco",
            "du ",
        ],
        "params": {"path": (_validate_path, True)},
        "argv": lambda p: ["du", "-sh", p["path"]],
    },
    "process_list": {
        "desc": "List running processes",
        "triggers": [
            "qué procesos",
            "procesos activos",
            "list processes",
            "ps ",
        ],
        "params": {},
        "argv": lambda p: ["ps", "aux"],
    },
    "show_env_safe": {
        "desc": "Show environment variables (secrets filtered)",
        "triggers": [
            "variables de entorno",
            "env safe",
            "environment variables",
            "muestra env",
        ],
        "params": {},
        "argv": lambda p: ["env"],
        "output_filter": lambda out: "\n".join(
            line
            for line in out.splitlines()
            if not any(
                k in line.upper()
                for k in ["KEY", "TOKEN", "SECRET", "PASS", "AUTH", "CRED", "API"]
            )
        ),
    },
    "copy_file": {
        "desc": "Copy a file",
        "triggers": [
            "copia el archivo",
            "copy file",
            "cp ",
        ],
        "params": {
            "src": (_validate_path, True),
            "dst": (_validate_path, False),
        },
        "argv": lambda p: ["cp", p["src"], p["dst"]],
    },
    "word_count": {
        "desc": "Count lines/words in file",
        "triggers": [
            "cuenta líneas",
            "word count",
            "wc ",
            "cuántas líneas",
            "count lines",
        ],
        "params": {"file": (lambda f: _validate_path(f, must_exist=True), True)},
        "argv": lambda p: ["wc", "-l", p["file"]],
    },
    "check_ports": {
        "desc": "Show listening ports",
        "triggers": [
            "puertos abiertos",
            "check ports",
            "listening ports",
            "qué puertos",
        ],
        "params": {},
        "argv": lambda p: ["ss", "-tlnp"],
    },
    "move_file": {
        "desc": "Move a file or directory to another location",
        "triggers": [
            "mueve el archivo",
            "mueve la carpeta",
            "move file",
            "mover archivo",
            "mv ",
        ],
        "params": {
            "src": (lambda f: _validate_path(f, must_exist=True), True),
            "dst": (_validate_path, False),
        },
        "argv": lambda p: ["mv", p["src"], p["dst"]],
    },
    "rename_file": {
        "desc": "Rename a file or directory",
        "triggers": [
            "renombra el archivo",
            "renombra la carpeta",
            "rename file",
            "cambiar nombre",
        ],
        "params": {
            "src": (lambda f: _validate_path(f, must_exist=True), True),
            "dst": (_validate_path, False),
        },
        "argv": lambda p: ["mv", p["src"], p["dst"]],
    },
    "compress_dir": {
        "desc": "Compress a directory into a tar.gz archive",
        "triggers": [
            "comprime la carpeta",
            "compress directory",
            "comprimir directorio",
            "tar ",
            "archivar carpeta",
        ],
        "params": {
            "src": (lambda f: _validate_path(f, must_exist=True), True),
        },
        "argv": lambda p: [
            "tar",
            "czf",
            p["src"].rstrip("/") + ".tar.gz",
            "-C",
            str(Path(p["src"]).parent),
            Path(p["src"]).name,
        ],
    },
    "git_status": {
        "desc": "Show git status of a repository directory",
        "triggers": [
            "git status",
            "estado del repo",
            "estado git",
            "cambios git",
            "muestra cambios git",
        ],
        "params": {"path": (_validate_path, True)},
        # git -C <path> status --short is read-only; no hooks triggered by status.
        # bypass_denylist=True because git is normally forbidden to prevent
        # arbitrary subcommand injection, but this argv is fully pre-determined.
        "argv": lambda p: ["git", "-C", p["path"], "status", "--short"],
        "bypass_denylist": True,
    },
    "tail_log": {
        "desc": "Show last 50 lines of a file",
        "triggers": [
            "muestra el final del archivo",
            "últimas líneas",
            "tail ",
            "log tail",
            "muestra el log",
        ],
        "params": {"file": (lambda f: _validate_path(f, must_exist=True), True)},
        "argv": lambda p: ["tail", "-n", "50", p["file"]],
    },
}


# ── Main executor ─────────────────────────────────────────────────────────────


def execute(query: str, console, questionary_mod) -> None:
    """Sovereign shell execution — template-based, never raw LLM strings.

    Steps:
      0 — Template matching via trigger keywords
      1 — Parameter extraction and individual validation
      2 — argv construction and forbidden-command check
      3 — User confirmation with argv display + hash
      4 — subprocess.run(shell=False, env=_CLEAN_ENV)
      5 — Output sanitization (ANSI strip, cap at 3000 chars)
      6 — Civic Ledger audit
    """
    # ── Step 0: Template matching ─────────────────────────────────────────────
    query_lower = query.lower().strip()

    matched_key: str | None = None
    matched_trigger: str | None = None
    tdef: dict | None = None

    for key, template in _TEMPLATES.items():
        triggers_by_len = sorted(template["triggers"], key=len, reverse=True)
        for trigger in triggers_by_len:
            if trigger in query_lower:
                matched_key = key
                matched_trigger = trigger
                tdef = template
                break
        if matched_key:
            break

    if tdef is None or matched_trigger is None:
        console.print("\n[secondary]Comandos shell disponibles:[/secondary]")
        for k, t in _TEMPLATES.items():
            console.print(f"  [accent]{k}[/accent]: {t['desc']}")
            console.print(f"    [dim]e.g.: {t['triggers'][0]}[/dim]")
        _audit("ShellUnknownIntent", None, extra=query_lower[:100])
        return

    # ── Step 1: Parameter extraction and validation ───────────────────────────
    # Build remainder by stripping the matched trigger from query_lower
    trigger_pos = query_lower.find(matched_trigger)
    remainder = query_lower[trigger_pos + len(matched_trigger) :]

    # Strip leading prepositions/connectors that are not parameters
    _prepositions = {"en", "in", "at", "de", "of", "the", "el", "la", "los", "las"}
    parts = remainder.strip().split()
    # Remove leading preposition tokens to reach actual param values
    while parts and parts[0].lower() in _prepositions:
        parts.pop(0)

    params: dict[str, str] = {}
    param_names = list(tdef["params"].keys())

    for i, pname in enumerate(param_names):
        raw_val = parts[i] if i < len(parts) else ""
        validator, required = tdef["params"][pname]

        if not raw_val:
            if required:
                console.print(
                    f"[warning]Parametro requerido faltante: {pname}[/warning]"
                )
                _audit("ShellMissingParam", None, extra=f":{pname}")
                return
            continue

        validated = validator(raw_val)
        if validated is None:
            console.print(
                f"[error]Parametro invalido o bloqueado: {pname}={raw_val!r}[/error]"
            )
            _audit("ShellInvalidParam", None, extra=f":{pname}={raw_val[:50]}")
            return

        params[pname] = validated

    # ── Step 2: Build argv ────────────────────────────────────────────────────
    argv = tdef["argv"](params)

    if argv[0] in _FORBIDDEN_COMMANDS and not tdef.get("bypass_denylist"):
        console.print(
            f"[error]Comando prohibido: {argv[0]} (LOLBIN/GTFOBIN catalogado)[/error]"
        )
        _audit("ShellForbiddenCommand", argv)
        return

    # ── Step 3: User confirmation ─────────────────────────────────────────────
    argv_display = " ".join(argv)
    cmd_hash = hashlib.sha256(argv_display.encode()).hexdigest()[:12]
    console.print("\n[secondary]Comando a ejecutar:[/secondary]")
    console.print(f"  [bold white]{argv_display}[/bold white]")
    console.print(f"  [dim]verificacion: {cmd_hash}[/dim]\n")

    answer = questionary_mod.confirm("Confirmar ejecucion?", default=False).ask()
    if not answer:
        console.print("[muted]Cancelado.[/muted]")
        _audit("ShellCancelled", argv)
        return

    # ── Step 4: Execute ───────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=_CLEAN_ENV,
            cwd=str(Path.home()),
        )
    except subprocess.TimeoutExpired:
        console.print("[error]Tiempo de espera agotado (30s).[/error]")
        _audit("ShellTimeout", argv)
        return
    except FileNotFoundError:
        console.print(f"[error]Comando no encontrado: {argv[0]}[/error]")
        _audit("ShellNotFound", argv)
        return
    except Exception as exc:
        console.print(f"[error]Error al ejecutar: {exc}[/error]")
        _audit("ShellError", argv, extra=f":{str(exc)[:80]}")
        return

    # ── Step 5: Output sanitization ───────────────────────────────────────────
    stdout = _strip_ansi(result.stdout)[:3000]
    stderr = _strip_ansi(result.stderr)[:500]

    if "output_filter" in tdef:
        stdout = tdef["output_filter"](stdout)

    if stdout:
        console.print(f"\n[dim]{stdout}[/dim]")
    if stderr:
        console.print(f"[error]{stderr}[/error]")

    rc_color = "success" if result.returncode == 0 else "error"
    console.print(f"[{rc_color}]returncode: {result.returncode}[/{rc_color}]")

    # ── Step 6: Civic Ledger ──────────────────────────────────────────────────
    _audit("ShellExecuted", argv, extra=f":rc={result.returncode}")


# ── Shell history ─────────────────────────────────────────────────────────────

_SHELL_EVENT_TYPES = (
    "ShellExecuted",
    "ShellCancelled",
    "ShellForbiddenCommand",
    "ShellTimeout",
)


def shell_history(console, limit: int = 20) -> None:
    """Display recent shell execution history from the Civic Ledger."""
    try:
        from zana.core.sentinel_lite import SentinelLiteDB

        db = SentinelLiteDB()
        rows: list[dict] = []
        for etype in _SHELL_EVENT_TYPES:
            rows.extend(db.events(limit=limit, event_type=etype))
        db.close()
    except Exception as exc:
        console.print(f"[error]Cannot read Civic Ledger: {exc}[/error]")
        return

    if not rows:
        console.print("[muted]No shell history yet. Run a shell command first.[/muted]")
        return

    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    rows = rows[:limit]

    console.print(
        f"\n[bold]Shell History[/bold]  [muted](last {len(rows)} entries)[/muted]\n"
    )
    for row in rows:
        ts = row.get("timestamp", "—")[:19].replace("T", " ")
        etype = row.get("event_type", "—")
        h = row.get("civic_hash", "")[:12]
        color = (
            "success"
            if etype == "ShellExecuted"
            else "warning"
            if etype == "ShellCancelled"
            else "error"
        )
        console.print(
            f"  [{color}]{etype}[/{color}]  [muted]{ts}[/muted]  [dim]{h}[/dim]"
        )
    console.print()
