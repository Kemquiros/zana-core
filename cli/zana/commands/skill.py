"""
skill.py — Z-Skill command implementations (local + Agora).

Local skill registry at ~/.zana/skills/:
  ~/.zana/skills/<name>/SKILL.md   — skill definition
  ~/.zana/skills/registry.json     — index of installed skills

The Agora — open skill marketplace (v1):
  Registry: AGORA_REGISTRY_URL (read-only, GitHub-hosted JSON)
  Publish:  generates submission payload; PR-based contribution flow
  Search:   fetches registry, filters by name/tags/description
  Adopt:    downloads SKILL.md from agora + installs locally

Commands:
  zana skill create <name>         — scaffold a new SKILL.md
  zana skill list                  — show installed skills
  zana skill run <name> <prompt>   — execute skill via ZSM dispatcher
  zana skill info <name>           — show full SKILL.md content
  zana skill publish <name>        — prepare skill for Agora submission
  zana skill search <query>        — search The Agora skill marketplace (default)
  zana skill search <query> --local — search installed local registry only (no network)
  zana skill adopt <name>          — install a skill from The Agora
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from rich.table import Table

from zana.tui.theme import console

SKILLS_DIR = Path.home() / ".zana" / "skills"
REGISTRY_PATH = SKILLS_DIR / "registry.json"
_SKILLS_DIR = SKILLS_DIR
_REGISTRY_PATH = REGISTRY_PATH

AGORA_REGISTRY_URL = (
    "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/registry.json"
)
AGORA_SUBMIT_URL = "https://github.com/Kemquiros/zana-agora/issues/new"
_AGORA_TIMEOUT = 8

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


def cmd_skill_create(
    name: str,
    author: str = "",
    description: str = "New Skill",
    domain: str = "general",
) -> None:
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


# ---------------------------------------------------------------------------
# Agora helpers
# ---------------------------------------------------------------------------


def _fetch_agora_registry() -> dict | None:
    """Fetch the remote Agora registry JSON. Returns None on network error."""
    try:
        with urlopen(AGORA_REGISTRY_URL, timeout=_AGORA_TIMEOUT) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, OSError):
        return None


def _civic_hash(content: str) -> str:
    """SHA-256 fingerprint of skill content (Z-Civic integrity marker)."""
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Agora commands
# ---------------------------------------------------------------------------


def cmd_skill_publish(name: str | None = None) -> None:
    """Generate an Agora submission artifact for a local skill."""
    registry = _load_registry()
    skills = registry.get("skills", [])

    if name is not None:
        entry = next((s for s in skills if s["name"] == name), None)
        if entry is None:
            console.print(
                f"[error]✗ Skill '{name}' not found in local registry.[/error]"
            )
            console.print("  List installed skills: [accent]zana skill list[/accent]")
            return
    else:
        if len(skills) == 1:
            entry = skills[0]
            name = entry["name"]
        else:
            if not skills:
                console.print(
                    "[error]✗ No skills installed. Create one with: [accent]zana skill create <name>[/accent][/error]"
                )
            else:
                console.print(
                    "[warning]Multiple skills installed. Specify a name:[/warning]"
                )
                for s in skills:
                    console.print(f"  [accent]{s['name']}[/accent]")
            return

    submission = {
        "name": entry["name"],
        "description": entry.get("description", ""),
        "version": entry.get("version", "1.0.0"),
        "tags": entry.get("tags", []),
        "author": entry.get("author", ""),
        "skill_url": "",
        "civic_hash": _civic_hash(
            json.dumps(entry, sort_keys=True, ensure_ascii=False)
        ),
    }

    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    submission_path = skill_dir / "agora_submission.json"
    tmp_path = submission_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(submission, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(tmp_path, submission_path)

    console.print(json.dumps(submission, indent=2, ensure_ascii=False))
    console.print(
        "\n[muted]To publish, open a PR at [accent]https://github.com/Kemquiros/zana-agora[/accent]"
        " adding this entry to registry.json[/muted]"
    )


def _cmd_skill_search_local(query: str) -> None:
    """Filter the local skill registry by keyword (no network required)."""
    registry = _load_registry()
    skills: list[dict] = registry.get("skills", [])
    q = query.lower()
    matches = [
        s
        for s in skills
        if q in s.get("name", "").lower()
        or q in s.get("description", "").lower()
        or q
        in " ".join(
            s.get("tags", []) if isinstance(s.get("tags"), list) else []
        ).lower()
    ]

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(
        f"[bold white]  Local Skills — {len(matches)} result(s) for '{query}'[/bold white]"
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not matches:
        console.print("[muted]  No local skills match that keyword.[/muted]")
        console.print(
            f'  Try the marketplace: [accent]zana skill search "{query}"[/accent]\n'
        )
        return

    table = Table(
        show_header=True, header_style="bold magenta", box=None, padding=(0, 2)
    )
    table.add_column("Name", style="accent", min_width=18)
    table.add_column("Version", style="muted", min_width=8)
    table.add_column("Description", min_width=30)
    table.add_column("Author", style="muted")

    for s in sorted(matches, key=lambda x: x["name"]):
        table.add_row(
            s.get("name", ""),
            s.get("version", "—"),
            s.get("description", "—"),
            s.get("author", "—"),
        )

    console.print(table)
    console.print(
        '\n  Run a skill: [accent]zana skill run <name> "your prompt"[/accent]\n'
    )


def cmd_skill_search(query: str, local: bool = False) -> None:
    """Search installed skills (--local) or The Agora marketplace (default)."""
    if local:
        _cmd_skill_search_local(query)
        return

    console.print(f"\n[muted]Searching The Agora for '{query}'…[/muted]")
    data = _fetch_agora_registry()

    if data is None:
        console.print(
            "[warning]⚠ Could not reach The Agora registry (offline or unavailable).[/warning]"
        )
        console.print("  Check your connection or try again later.\n")
        return

    skills: list[dict] = data.get("skills", [])
    q = query.lower()
    matches = [
        s
        for s in skills
        if q in s.get("name", "").lower()
        or q in s.get("description", "").lower()
        or q in " ".join(s.get("tags", [])).lower()
    ]

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(
        f"[bold white]  The Agora — {len(matches)} result(s) for '{query}'[/bold white]"
    )
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not matches:
        console.print("[muted]  No skills found. Try a different keyword.[/muted]\n")
        return

    table = Table(
        show_header=True, header_style="bold magenta", box=None, padding=(0, 2)
    )
    table.add_column("Name", style="accent", min_width=20)
    table.add_column("Ver", style="muted", min_width=6)
    table.add_column("Description", min_width=36)
    table.add_column("Author", style="muted", min_width=12)
    table.add_column("Tags", style="muted")

    for s in matches:
        tags = (
            ", ".join(s.get("tags", []))
            if isinstance(s.get("tags"), list)
            else s.get("tags", "")
        )
        table.add_row(
            s.get("name", ""),
            s.get("version", ""),
            s.get("description", ""),
            s.get("author", ""),
            tags,
        )

    console.print(table)
    console.print("\n  Adopt a skill: [accent]zana skill adopt <name>[/accent]\n")


def cmd_skill_adopt(name: str) -> None:
    """Download and install a skill from The Agora into ~/.zana/skills/."""
    # Check if already installed
    skill_dir = SKILLS_DIR / name
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.exists():
        console.print(f"[warning]⚠ Skill '{name}' is already installed.[/warning]")
        console.print(f"  Path: [accent]{skill_md_path}[/accent]")
        console.print(
            f"  To update: delete the folder and run [accent]zana skill adopt {name}[/accent] again.\n"
        )
        return

    console.print(f"\n[muted]Fetching '{name}' from The Agora…[/muted]")
    data = _fetch_agora_registry()

    if data is None:
        console.print(
            "[warning]⚠ Could not reach The Agora registry (offline or unavailable).[/warning]"
        )
        console.print("  Check your connection or try again later.\n")
        return

    skills: list[dict] = data.get("skills", [])
    entry = next((s for s in skills if s.get("name") == name), None)

    if entry is None:
        console.print(f"[error]✗ Skill '{name}' not found in The Agora.[/error]")
        console.print(f"  Search first: [accent]zana skill search {name}[/accent]\n")
        return

    skill_url: str = entry.get("skill_url", "")
    if not skill_url:
        console.print(
            f"[error]✗ Skill '{name}' has no download URL in the registry.[/error]\n"
        )
        return

    try:
        with urlopen(skill_url, timeout=_AGORA_TIMEOUT) as resp:  # noqa: S310
            skill_content = resp.read().decode()
    except (URLError, OSError) as exc:
        console.print(f"[error]✗ Failed to download skill: {exc}[/error]\n")
        return

    # Z-Civic integrity check
    expected_hash = entry.get("civic_hash", "")
    actual_hash = _civic_hash(skill_content)
    if expected_hash and expected_hash != actual_hash:
        console.print(
            "[error]✗ Civic integrity check failed — skill content may have been tampered with.[/error]"
        )
        console.print(f"  Expected: [muted]{expected_hash}[/muted]")
        console.print(f"  Got:      [muted]{actual_hash}[/muted]\n")
        return

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md_path.write_text(skill_content, encoding="utf-8")
    _register_skill(name, skill_dir)

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"[success]✓ Skill '{name}' adopted from The Agora.[/success]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")
    console.print(f"  Version:   [accent]{entry.get('version', '?')}[/accent]")
    console.print(f"  Author:    [muted]{entry.get('author', '—')}[/muted]")
    console.print(f"  Civic ID:  [muted]{actual_hash}[/muted]")
    console.print(f"  Path:      [muted]{skill_md_path}[/muted]\n")
    console.print(f'  Run it: [accent]zana skill run {name} "your prompt"[/accent]\n')


# ---------------------------------------------------------------------------
# Z-Skills v2.0 commands — update, rate
# ---------------------------------------------------------------------------


def cmd_skill_update(name: str | None = None) -> None:
    """Check for newer versions of installed skills in the Agora."""
    agora_registry = _fetch_agora_registry()
    if agora_registry is None:
        console.print(
            "[warning]⚠ Could not reach The Agora registry (offline or unavailable).[/warning]"
        )
        return

    registry = _load_registry()
    installed: list[dict] = registry.get("skills", [])
    agora_map: dict[str, dict] = {
        s["name"]: s for s in agora_registry.get("skills", [])
    }

    if name is not None:
        entry = next((s for s in installed if s["name"] == name), None)
        if entry is None:
            console.print(
                f"[error]✗ Skill '{name}' not found in local registry.[/error]"
            )
            return
        skills_to_check = [entry]
    else:
        skills_to_check = installed

    for skill in skills_to_check:
        skill_name = skill["name"]
        if skill_name not in agora_map:
            console.print(f"[muted]{skill_name}: not in Agora[/muted]")
            continue
        agora_version = agora_map[skill_name].get("version", "0.0.0")
        local_version = skill.get("version", "0.0.0")
        if agora_version > local_version:
            console.print(
                f"[accent]{skill_name}[/accent]: updating {local_version} → {agora_version}"
            )
            cmd_skill_adopt(skill_name)
        else:
            console.print(
                f"[success]{skill_name} is up to date ({local_version})[/success]"
            )


def cmd_skill_rate(name: str, rating: int) -> None:
    """Save a local rating (1-5) for an installed skill."""
    if rating < 1 or rating > 5:
        console.print(f"[error]✗ Rating must be between 1 and 5, got {rating}.[/error]")
        return

    registry = _load_registry()
    skills: list[dict] = registry.get("skills", [])
    entry = next((s for s in skills if s["name"] == name), None)

    if entry is None:
        console.print(f"[error]✗ Skill '{name}' not found in local registry.[/error]")
        return

    entry["rating"] = rating
    _save_registry(registry)

    stars = "★" * rating + "☆" * (5 - rating)
    console.print(f"[success]✓ Rated '{name}': {stars} ({rating}/5)[/success]")
