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
  zana skill search <query>        — search The Agora skill marketplace
  zana skill adopt <name>          — install a skill from The Agora
"""

from __future__ import annotations

import hashlib
import json
import re
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from rich.table import Table

from zana.tui.theme import console

SKILLS_DIR = Path.home() / ".zana" / "skills"
REGISTRY_PATH = SKILLS_DIR / "registry.json"

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


def cmd_skill_publish(name: str, open_browser: bool = True) -> None:
    """Prepare a skill for submission to The Agora (open skill marketplace)."""
    skill_dir = SKILLS_DIR / name
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        console.print(f"[error]✗ Skill '{name}' not found locally.[/error]")
        console.print("  Create it first: [accent]zana skill create {name}[/accent]")
        return

    content = skill_md_path.read_text(encoding="utf-8")
    meta = _parse_frontmatter(content)
    civic = _civic_hash(content)

    payload = {
        "name": meta.get("name", name),
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
        "author": meta.get("author", "anonymous"),
        "tags": meta.get("tags", "[]"),
        "zana_version": meta.get("zana_version", ">=3.5.0"),
        "civic_hash": civic,
        "submitted_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "skill_content": content,
    }

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold white]  The Agora — Skill Submission[/bold white]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")
    console.print(
        f"  Skill:     [accent]{payload['name']}[/accent] v{payload['version']}"
    )
    console.print(f"  Author:    [muted]{payload['author']}[/muted]")
    console.print(f"  Civic ID:  [muted]{civic}[/muted]")
    console.print(f"  Tags:      [muted]{payload['tags']}[/muted]\n")

    # Write submission JSON to ~/.zana/skills/<name>/agora_submission.json
    submission_path = skill_dir / "agora_submission.json"
    submission_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(f"  Submission saved: [accent]{submission_path}[/accent]\n")

    console.print("  [bold]Next steps to publish to The Agora:[/bold]")
    console.print("  1. Open a GitHub issue at the link below")
    console.print(
        "  2. Attach your [accent]SKILL.md[/accent] and paste the submission JSON"
    )
    console.print(
        "  3. A maintainer will review and merge — open-source skills are always free\n"
    )
    console.print(
        f"  [accent]{AGORA_SUBMIT_URL}?title=Skill+Submission:+{name}&labels=skill-submission[/accent]\n"
    )

    if open_browser:
        issue_url = (
            f"{AGORA_SUBMIT_URL}?title=Skill+Submission:+{name}&labels=skill-submission"
        )
        try:
            webbrowser.open(issue_url)
            console.print("  [muted]→ Opened submission URL in your browser.[/muted]\n")
        except Exception:
            pass


def cmd_skill_search(query: str) -> None:
    """Search The Agora open skill marketplace."""
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
