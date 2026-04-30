import os
import subprocess
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

import typer

from cli.tui.theme import console

REPO          = "Kemquiros/zana-core"
RELEASES_API  = f"https://api.github.com/repos/{REPO}/releases/latest"
COMMITS_API   = f"https://api.github.com/repos/{REPO}/commits/main"
GIT_INSTALL   = f"zana @ git+https://github.com/{REPO}.git#subdirectory=cli"
PACKAGE_NAME  = "zana"


def _current_version() -> str:
    try:
        return pkg_version(PACKAGE_NAME)
    except Exception:
        return "unknown"


def _latest_release_version() -> str | None:
    try:
        import httpx
        r = httpx.get(
            RELEASES_API, timeout=8,
            headers={"Accept": "application/vnd.github+json"},
        )
        r.raise_for_status()
        tag = r.json().get("tag_name", "")
        return tag.lstrip("v") or None
    except Exception:
        return None


def _latest_commit_sha() -> str | None:
    """Return the short SHA of the latest commit on main."""
    try:
        import httpx
        r = httpx.get(COMMITS_API, timeout=8,
                      headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        return r.json().get("sha", "")[:7]
    except Exception:
        return None


def _do_upgrade() -> bool:
    """Install the latest CLI directly from the main branch. Returns True on success."""
    if not sys.executable:
        return False

    uv = _find_uv()
    if uv:
        cmd = [uv, "tool", "install", GIT_INSTALL, "--force", "--quiet"]
    else:
        cmd = [sys.executable, "-m", "pip", "install",
               f"git+https://github.com/{REPO}.git#subdirectory=cli",
               "--upgrade", "--quiet"]

    result = subprocess.run(cmd)
    return result.returncode == 0


def _find_uv() -> str | None:
    import shutil
    uv = shutil.which("uv")
    if uv:
        return uv
    uv_home = Path.home() / ".local" / "bin" / "uv"
    return str(uv_home) if uv_home.exists() else None


def _pull_local_repo() -> bool:
    """If the repo was cloned locally, fast-forward it to origin/main."""
    repo_dir = Path(os.getenv("ZANA_CORE_DIR", "")) or Path.home() / ".zana" / "core-repo"
    if not (repo_dir / ".git").exists():
        return False
    try:
        subprocess.run(
            ["git", "fetch", "--all"],
            cwd=str(repo_dir), capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            cwd=str(repo_dir), capture_output=True, check=True,
        )
        return True
    except Exception:
        return False


def cmd_upgrade(check_only: bool = False, no_interactive: bool = False) -> None:
    current = _current_version()
    console.print(f"\n[muted]Versión instalada: {current}[/muted]")
    console.print("[muted]Consultando GitHub...[/muted]")

    release_ver = _latest_release_version()
    commit_sha  = _latest_commit_sha()

    # Determine if an upgrade is available
    if release_ver and release_ver != current:
        label = f"v{release_ver}"
        needs_upgrade = True
    elif commit_sha:
        label = f"main@{commit_sha}"
        # Always offer — commit-based installs never match a version string
        needs_upgrade = True
    else:
        console.print("[warning]No se pudo contactar GitHub. Verifica tu conexión.[/warning]")
        needs_upgrade = False

    if not needs_upgrade:
        console.print(f"[success]ZANA ya está al día ({current}).[/success]")
        return

    console.print(f"[accent]Actualización disponible:[/accent] {label}")

    if check_only:
        console.print("[muted]Ejecuta `zana upgrade` para instalar.[/muted]")
        return

    if not no_interactive:
        confirm = typer.confirm("  ¿Iniciar el Protocolo de Ascensión (upgrade)?", default=True)
        if not confirm:
            console.print("[muted]Upgrade cancelado.[/muted]")
            return

    console.print("\n[primary]Actualizando Córtex...[/primary]")

    # Step 1: pull the local repo clone if it exists
    if _pull_local_repo():
        console.print("[muted]Repositorio local sincronizado con origin/main.[/muted]")

    # Step 2: reinstall the CLI from git
    if _do_upgrade():
        console.print(f"[success]✅ ZANA Córtex actualizado exitosamente.[/success]")
        console.print("[muted]Reinicia tu terminal para aplicar cambios de PATH.[/muted]")
        console.print("[muted]Juntos hacemos temblar los cielos.[/muted]")
    else:
        console.print("[error]El upgrade automático falló.[/error]")
        console.print("[yellow]Solución manual:[/yellow]")
        console.print("  [accent]bash <(curl -LsSf https://zana.vecanova.com/install.sh)[/accent]")
        raise typer.Exit(1)
