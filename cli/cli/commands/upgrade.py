import sys
from importlib.metadata import version as pkg_version

import httpx
import typer

from cli.tui.theme import console

RELEASES_API = "https://api.github.com/repos/kemquiros/zana-core/releases/latest"
PACKAGE_NAME = "zana"


def _latest_version() -> str | None:
    try:
        r = httpx.get(
            RELEASES_API, timeout=8, headers={"Accept": "application/vnd.github+json"}
        )
        r.raise_for_status()
        tag = r.json().get("tag_name", "")
        return tag.lstrip("v")
    except Exception:
        return None


def _current_version() -> str:
    try:
        return pkg_version(PACKAGE_NAME)
    except Exception:
        return "unknown"


def cmd_upgrade(check_only: bool = False) -> None:
    current = _current_version()
    console.print(f"[muted]Current version: {current}[/muted]")
    console.print("[muted]Checking GitHub Releases...[/muted]")

    latest = _latest_version()

    if latest is None:
        console.print("[warning]Could not reach GitHub Releases API.[/warning]")
        raise typer.Exit(1)

    if latest == current:
        console.print(f"[success]Already up to date ({current}).[/success]")
        return

    console.print(f"[accent]New version available: {latest}[/accent]")

    if check_only:
        console.print("[muted]Run `zana upgrade` to install.[/muted]")
        return

    console.print("[primary]Upgrading...[/primary]")
    import subprocess
    import shutil

    if shutil.which("uv"):
        cmd = ["uv", "tool", "install", f"zana=={latest}", "--force"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", f"zana=={latest}"]

    result = subprocess.run(cmd)
    if result.returncode == 0:
        console.print(f"[success]Upgraded to {latest}.[/success]")
    else:
        console.print(
            "[error]Upgrade failed. Try: uv tool install zana --force[/error]"
        )
        raise typer.Exit(1)
