"""
skill.py — Z-Skill v1.0 command implementations.

Local skill registry at ~/.zana/skills/:
  ~/.zana/skills/<name>/SKILL.md   — skill definition
  ~/.zana/skills/registry.json     — index of installed skills

Commands:
  zana skill create <name>   — scaffold a new SKILL.md
  zana skill list            — show installed skills
  zana skill run <name> <prompt> — execute skill via ZSM dispatcher
  zana skill info <name>     — show full SKILL.md content
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from rich.table import Table

from zana.tui.theme import console

SKILLS_DIR = Path.home() / ".zana" / "skills"
REGISTRY_PATH = SKILLS_DIR / "registry.json"

_SKILL_MD_TEMPLATE = """\
---
name: {name}
version: 1.0.0
description: One-line description of what this skill does
author: {author}
tags: []
zana_version: ">=3.5.0"
created_at: {created_at}
---

## Trigger

Phrases or patterns that activate this skill. Example:
- "summarize my notes"
- "create a report for"

## Steps

1. Step one — describe what the skill does
2. Step two — continue
3. Step three — final output

## Examples

- Input: "example user prompt"
  Output: "expected skill response"
"""


def _load_registry() -> dict:
    """Return the registry index, creating it if it does not exist."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps({"skills": []}, indent=2))
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"skills": []}


def _save_registry(data: dict) -> None:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _parse_frontmatter(skill_md: str) -> dict:
    """Extract key: value pairs from the YAML frontmatter block."""
    match = re.match(r"^---\n(.*?)\n---", skill_md, re.DOTALL)
    if not match:
        return {}
    meta: dict = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta


def _register_skill(name: str, skill_dir: Path) -> None:
    """Add or update a skill entry in registry.json."""
    skill_md_path = skill_dir / "SKILL.md"
    meta = (
        _parse_frontmatter(skill_md_path.read_text()) if skill_md_path.exists() else {}
    )

    entry = {
        "name": name,
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
        "author": meta.get("author", ""),
        "tags": meta.get("tags", "[]"),
        "path": str(skill_dir),
        "installed_at": datetime.now(UTC).isoformat(),
    }

    registry = _load_registry()
    registry["skills"] = [s for s in registry["skills"] if s["name"] != name]
    registry["skills"].append(entry)
    _save_registry(registry)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_skill_create(name: str, author: str = "") -> None:
    """Scaffold a new SKILL.md at ~/.zana/skills/<name>/."""
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        console.print(
            "[error]✗ Skill name must be lowercase alphanumeric, hyphens and underscores only.[/error]"
        )
        return

    skill_dir = SKILLS_DIR / name
    skill_md_path = skill_dir / "SKILL.md"

    if skill_md_path.exists():
        console.print(
            f"[warning]⚠ Skill '{name}' already exists at {skill_dir}[/warning]"
        )
        console.print(f"  Edit it directly: [accent]{skill_md_path}[/accent]")
        return

    skill_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC).strftime("%Y-%m-%d")
    skill_md_path.write_text(
        _SKILL_MD_TEMPLATE.format(
            name=name, author=author or "anonymous", created_at=created_at
        ),
        encoding="utf-8",
    )
    _register_skill(name, skill_dir)

    console.print(f"\n[success]✓ Skill '{name}' created.[/success]")
    console.print(f"  Path: [accent]{skill_md_path}[/accent]")
    console.print(
        "\n  Edit [accent]SKILL.md[/accent] to define triggers, steps, and examples."
    )
    console.print(
        f'  Run it with: [accent]zana skill run {name} "your prompt"[/accent]\n'
    )


def cmd_skill_list() -> None:
    """List all skills installed in the local registry."""
    registry = _load_registry()
    skills = registry.get("skills", [])

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(
        f"[bold white]  Z-Skill Registry — {len(skills)} skill(s) installed[/bold white]"
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not skills:
        console.print("[muted]  No skills installed yet.[/muted]")
        console.print("  Create one with: [accent]zana skill create <name>[/accent]\n")
        return

    table = Table(
        show_header=True, header_style="bold magenta", box=None, padding=(0, 2)
    )
    table.add_column("Name", style="accent", min_width=18)
    table.add_column("Version", style="muted", min_width=8)
    table.add_column("Description", min_width=30)
    table.add_column("Author", style="muted")

    for skill in sorted(skills, key=lambda s: s["name"]):
        table.add_row(
            skill["name"],
            skill.get("version", "—"),
            skill.get("description", "—"),
            skill.get("author", "—"),
        )

    console.print(table)
    console.print()


def cmd_skill_run(name: str, prompt: str) -> None:
    """Execute a skill by running its prompt through the ZSM dispatcher."""
    skill_dir = SKILLS_DIR / name
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        console.print(f"[error]✗ Skill '{name}' not found at {skill_dir}[/error]")
        console.print("  List installed skills: [accent]zana skill list[/accent]")
        return

    skill_content = skill_md_path.read_text(encoding="utf-8")
    meta = _parse_frontmatter(skill_content)

    console.print(
        f"\n[primary]SKILL RUN[/primary] [muted]{name} v{meta.get('version', '?')}[/muted]\n"
    )

    # Build enriched prompt: inject skill context into user prompt
    enriched_prompt = (
        f"[SKILL: {name}]\nSkill definition:\n{skill_content}\n\nUser request: {prompt}"
    )

    try:
        from zana.core.zsm import ZSM

        zsm = ZSM()
        response = zsm.respond_text(enriched_prompt)
        console.print(response)
    except Exception as e:
        console.print(f"[warning]ZSM unavailable: {e}[/warning]")
        console.print(
            "[muted]Skill loaded but execution requires ZSM or an active LLM.[/muted]"
        )
        console.print("\n[muted]Skill context passed to prompt:[/muted]")
        console.print(f"  [accent]{meta.get('description', skill_md_path)}[/accent]")

    console.print()


def cmd_skill_info(name: str) -> None:
    """Display the full SKILL.md for an installed skill."""
    skill_dir = SKILLS_DIR / name
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        console.print(f"[error]✗ Skill '{name}' not found.[/error]")
        return

    meta = _parse_frontmatter(skill_md_path.read_text(encoding="utf-8"))

    console.print(f"\n[bold]{name}[/bold] [muted]v{meta.get('version', '?')}[/muted]")
    console.print(f"[muted]{meta.get('description', '')}[/muted]")
    console.print(
        f"[muted]Author: {meta.get('author', '—')} · Path: {skill_dir}[/muted]\n"
    )
    console.print(skill_md_path.read_text(encoding="utf-8"))
