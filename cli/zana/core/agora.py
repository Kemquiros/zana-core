"""
agora.py — The Agora: GitHub-hosted skill registry client.

Provides a pure-stdlib HTTP client for the Agora skill marketplace.
All network errors are handled gracefully (log + fallback).
No subprocess, no shell=True, no third-party dependencies.

Registry JSON format (registry.json):
  {
    "version": "1.0",
    "skills": [
      {
        "id": "daily-planner",
        "name": "daily-planner",
        "version": "1.0.0",
        "description": "...",
        "author": "JohnDoe",
        "tags": ["productivity"],
        "skill_url": "https://...",
        "civic_hash": "sha256:..."
      }
    ]
  }
"""

from __future__ import annotations

import io
import json
import logging
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

AGORA_REGISTRY_URL = (
    "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/registry.json"
)
AGORA_SUBMIT_REPO = "Kemquiros/zana-agora"
_AGORA_TIMEOUT = 8


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def fetch_registry() -> list[dict]:
    """Download and parse the Agora registry JSON.

    Returns an empty list on any network or parse error so callers can
    degrade gracefully without branching on None.
    """
    try:
        req = urllib.request.Request(
            AGORA_REGISTRY_URL,
            headers={"Accept": "application/json", "User-Agent": "zana-cli"},
        )
        with urllib.request.urlopen(req, timeout=_AGORA_TIMEOUT) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
            if isinstance(payload, list):
                return payload
            # Standard envelope: {"version": "...", "skills": [...]}
            return payload.get("skills", []) if isinstance(payload, dict) else []
    except (urllib.error.URLError, json.JSONDecodeError, OSError, ValueError) as exc:
        logger.warning("Agora registry fetch failed: %s", exc)
        return []


def search_registry(query: str, registry: list[dict]) -> list[dict]:
    """Filter *registry* by *query* against name, tags, and description.

    Comparison is case-insensitive. An empty query returns all entries.
    """
    if not query:
        return list(registry)
    q = query.lower()
    results: list[dict] = []
    for skill in registry:
        name = skill.get("name", "").lower()
        description = skill.get("description", "").lower()
        tags_raw = skill.get("tags", [])
        tags = (
            " ".join(tags_raw).lower()
            if isinstance(tags_raw, list)
            else str(tags_raw).lower()
        )
        if q in name or q in description or q in tags:
            results.append(skill)
    return results


# ---------------------------------------------------------------------------
# Pack
# ---------------------------------------------------------------------------


def pack_skill(skill_dir: Path) -> bytes:
    """Zip *skill_dir* into an in-memory .zsk archive and return the bytes.

    Raises:
        FileNotFoundError: if *skill_dir* does not contain a SKILL.md file.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(
            f"SKILL.md not found in {skill_dir}. "
            "Run 'zana skill create <name>' to scaffold a valid skill."
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(skill_dir))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


def publish_skill_to_agora(skill_name: str, skill_dir: Path, github_token: str) -> str:
    """Open a GitHub issue in the zana-agora repo to submit a skill.

    Uses the GitHub REST API (POST /repos/{owner}/{repo}/issues).
    Returns the URL of the created issue.

    Raises:
        ValueError: if *github_token* is empty or whitespace.
        urllib.error.HTTPError: on API errors (4xx/5xx).
    """
    if not github_token or not github_token.strip():
        raise ValueError(
            "A GitHub personal access token is required to publish to The Agora. "
            "Pass it via --github-token or set GITHUB_TOKEN in your environment."
        )

    skill_md = skill_dir / "SKILL.md"
    skill_md_content = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""

    # Build metadata JSON from frontmatter when available
    submission_meta: dict = {
        "skill_name": skill_name,
        "skill_dir": str(skill_dir),
        "skill_md_preview": skill_md_content[:500],
    }

    issue_body = (
        "## Agora Skill Submission\n\n"
        f"**Skill:** `{skill_name}`\n\n"
        "### Submission Metadata\n\n"
        f"```json\n{json.dumps(submission_meta, indent=2, ensure_ascii=False)}\n```\n\n"
        "_Submitted via `zana skill publish --agora`_"
    )

    payload = json.dumps(
        {
            "title": f"[SKILL SUBMISSION] {skill_name}",
            "body": issue_body,
            "labels": ["skill-submission"],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    api_url = f"https://api.github.com/repos/{AGORA_SUBMIT_REPO}/issues"
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {github_token.strip()}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "zana-cli",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=_AGORA_TIMEOUT) as resp:  # noqa: S310
        response_data = json.loads(resp.read().decode("utf-8"))

    issue_url: str = response_data.get("html_url", "")
    return issue_url


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


def install_skill_from_agora(skill_id: str, target_dir: Path) -> Path:
    """Download a .zsk archive from the Agora and extract it to *target_dir*.

    The registry entry for *skill_id* must contain a ``skill_url`` field
    pointing to either a raw SKILL.md or a .zsk zip archive.

    Returns the path to the installed skill directory (target_dir / skill_id).

    Raises:
        KeyError: if *skill_id* is not found in the registry.
        urllib.error.URLError: on download failure.
    """
    registry = fetch_registry()
    entry = next(
        (s for s in registry if s.get("id") == skill_id or s.get("name") == skill_id),
        None,
    )
    if entry is None:
        raise KeyError(f"Skill '{skill_id}' not found in the Agora registry.")

    skill_url: str = entry.get("skill_url", "")
    if not skill_url:
        raise ValueError(
            f"Skill '{skill_id}' has no download URL in the Agora registry."
        )

    req = urllib.request.Request(
        skill_url,
        headers={"User-Agent": "zana-cli"},
    )
    with urllib.request.urlopen(req, timeout=_AGORA_TIMEOUT) as resp:  # noqa: S310
        content = resp.read()

    skill_install_dir = target_dir / skill_id
    skill_install_dir.mkdir(parents=True, exist_ok=True)

    # Detect .zsk (zip) vs raw SKILL.md
    if skill_url.endswith(".zsk") or (len(content) > 2 and content[:2] == b"PK"):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(skill_install_dir)
    else:
        # Raw SKILL.md content
        (skill_install_dir / "SKILL.md").write_bytes(content)

    return skill_install_dir
