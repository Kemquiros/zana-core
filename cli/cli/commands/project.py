from pathlib import Path
from typing import Optional

from cli.tui.theme import console

ZANA_PROJECTS_DIR = Path.home() / ".zana" / "projects"
CURRENT_PROJECT_LINK = Path.home() / ".zana" / "current_project"


def _get_active_project() -> Optional[str]:
    if CURRENT_PROJECT_LINK.exists() and CURRENT_PROJECT_LINK.is_symlink():
        return CURRENT_PROJECT_LINK.resolve().name
    return None


def cmd_project_init(name: str) -> None:
    """Initializes a new project workspace."""
    proj_dir = ZANA_PROJECTS_DIR / name
    if proj_dir.exists():
        console.print(f"[warning]Project '{name}' already exists.[/warning]")
        return

    proj_dir.mkdir(parents=True, exist_ok=True)

    env_file = proj_dir / ".env.project"
    env_file.write_text(
        f"ZANA_PROJECT_NAME={name}\nZANA_COLLECTION_PREFIX={name}_memory\n"
    )

    console.print(f"[success]Cognitive context for project '{name}' initialized.[/success]")
    cmd_project_switch(name)


def cmd_project_switch(name: str) -> None:
    """Switches the active project context."""
    proj_dir = ZANA_PROJECTS_DIR / name
    if not proj_dir.exists():
        console.print(f"[error]Project '{name}' not found.[/error]")
        return

    if CURRENT_PROJECT_LINK.exists():
        CURRENT_PROJECT_LINK.unlink()

    CURRENT_PROJECT_LINK.symlink_to(proj_dir)
    console.print(
        f"🌀 [accent]Context Switched:[/accent] Memory and reasoning are now isolated to [primary]{name}[/primary]."
    )


def cmd_project_current() -> None:
    """Shows the active project context."""
    active = _get_active_project()
    if active:
        console.print(f"Active Context: [primary]{active}[/primary]")
    else:
        console.print("Active Context: [muted]Global (Default)[/muted]")


def cmd_project_list() -> None:
    """Lists all initialized projects."""
    if not ZANA_PROJECTS_DIR.exists():
        console.print("[muted]No projects initialized yet.[/muted]")
        return

    active = _get_active_project()
    console.print("\n[primary]Sovereign Projects (Contexts):[/primary]")

    for p in ZANA_PROJECTS_DIR.iterdir():
        if p.is_dir():
            marker = "[success]●[/success]" if p.name == active else "○"
            console.print(f"  {marker} {p.name}")
    console.print()
