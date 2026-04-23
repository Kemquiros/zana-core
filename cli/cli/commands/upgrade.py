import os
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

    if os.getenv("TAURI_ENV") == "true":
        console.print("[muted]Note: Desktop App updates are handled automatically via the UI.[/muted]")

    if check_only:
        console.print("[muted]Run `zana upgrade` to install.[/muted]")
        return

    console.print("\n[primary]Updating Córtex...[/primary]")
    import subprocess
    import shutil

    # Force uv to install from git for the latest master features if we are on dev,
    # or use the tagged version if we are on production.
    if shutil.which("uv"):
        # For sovereignty and latest master features
        cmd = ["uv", "tool", "install", "zana @ git+https://github.com/kemquiros/zana-core.git#subdirectory=cli", "--force", "--quiet"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "zana", "--quiet"]

    try:
        subprocess.run(cmd, check=True)
        console.print(f"[success]ZANA Córtex upgraded to {latest} successfully.[/success]")
        console.print("[muted]Juntos hacemos temblar los cielos.[/muted]")
    except subprocess.CalledProcessError:
        console.print(
            "[error]Upgrade failed. Try: uv tool install zana --force[/error]"
        )
        raise typer.Exit(1)
