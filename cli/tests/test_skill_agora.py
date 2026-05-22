"""Tests for S15-2: Agora remote search and skill adopt.

Covers cmd_skill_search (remote) and cmd_skill_adopt end-to-end with
offline/network-error/already-installed/not-found scenarios.

NOTE: Both commands were fully implemented prior to Sprint 15. These tests
provide focused coverage of the Agora (remote) paths specifically.
"""

from __future__ import annotations

import pytest
from zana.commands.skill import _civic_hash

# ---------------------------------------------------------------------------
# Fixtures — registry isolation (mirrors test_skill.py pattern)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_skills(tmp_path, monkeypatch):
    """Redirect SKILLS_DIR and REGISTRY_PATH to tmp_path for every test."""
    skills_dir = tmp_path / "skills"
    registry = skills_dir / "registry.json"
    monkeypatch.setattr("zana.commands.skill.SKILLS_DIR", skills_dir)
    monkeypatch.setattr("zana.commands.skill.REGISTRY_PATH", registry)
    yield skills_dir, registry


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_SKILL_CONTENT = """\
---
name: daily-planner
version: 1.0.0
description: Daily planning assistant
author: JohnDoe
tags: [productivity]
zana_version: ">=3.5.0"
created_at: 2026-05-21
---

## Trigger
plan my day

## Steps
1. Ask for priorities
2. Create schedule
"""

MOCK_AGORA_REGISTRY = {
    "version": "1.0",
    "skills": [
        {
            "name": "daily-planner",
            "description": "Helps organize daily tasks and priorities",
            "version": "1.0.0",
            "author": "JohnDoe",
            "tags": ["productivity", "planning"],
            "skill_url": "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/skills/daily-planner/SKILL.md",
            "civic_hash": _civic_hash(MOCK_SKILL_CONTENT),
        },
        {
            "name": "recipe-finder",
            "description": "Find recipes based on available ingredients",
            "version": "1.2.0",
            "author": "CookBot",
            "tags": ["cooking", "recipes"],
            "skill_url": "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/skills/recipe-finder/SKILL.md",
            "civic_hash": "sha256:abcdefabcdef1234",
        },
    ],
}


class _FakeResponse:
    """Minimal context-manager response for urlopen mocking."""

    def __init__(self, content: bytes):
        self._content = content

    def read(self) -> bytes:
        return self._content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


# ---------------------------------------------------------------------------
# cmd_skill_search — remote Agora paths
# ---------------------------------------------------------------------------


def test_skill_search_remote_returns_matches(monkeypatch):
    """Agora registry with matching skills renders without error."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity")  # must not raise


def test_skill_search_remote_match_by_name(monkeypatch):
    """Query matching skill name produces no exception."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("daily-planner")  # must not raise


def test_skill_search_remote_match_by_tag(monkeypatch):
    """Query matching a tag produces no exception."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("cooking")  # matches recipe-finder via tag


def test_skill_search_remote_no_results(monkeypatch):
    """Query with no remote matches prints helpful message without crashing."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("quantum_cooking_blockchain")  # clearly no match


def test_skill_search_falls_back_gracefully_when_offline(monkeypatch):
    """Agora returns None (offline) → warning is printed, no exception raised."""
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity")  # must not raise


def test_skill_search_local_flag_does_not_hit_agora(monkeypatch):
    """--local flag must never call _fetch_agora_registry."""
    called = []
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry",
        lambda: called.append(True) or {},
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity", local=True)
    assert called == [], "--local must not hit the network"


# ---------------------------------------------------------------------------
# cmd_skill_adopt — download and install paths
# ---------------------------------------------------------------------------


def test_skill_adopt_success(isolated_skills, monkeypatch):
    """Valid skill in Agora → SKILL.md written to ~/.zana/skills/<name>/."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: _FakeResponse(MOCK_SKILL_CONTENT.encode()),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    assert (skills_dir / "daily-planner" / "SKILL.md").exists()


def test_skill_adopt_registers_in_local_registry(isolated_skills, monkeypatch):
    """After adopt, skill appears in registry.json."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: _FakeResponse(MOCK_SKILL_CONTENT.encode()),
    )
    from zana.commands.skill import _load_registry, cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    registry = _load_registry()
    names = [s["name"] for s in registry["skills"]]
    assert "daily-planner" in names


def test_skill_adopt_already_installed_does_not_download(isolated_skills, monkeypatch):
    """Skill SKILL.md already present → warning shown, urlopen never called."""
    skills_dir, _ = isolated_skills
    # Pre-create the skill file (mimics already-installed state)
    skill_dir = skills_dir / "daily-planner"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("existing content")

    download_called = []
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: download_called.append(True),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    assert download_called == [], "urlopen must not be called when skill is installed"
    # File must remain untouched
    assert (skill_dir / "SKILL.md").read_text() == "existing content"


def test_skill_adopt_not_found_in_agora(isolated_skills, monkeypatch):
    """Skill not in remote registry → error message, no download, no crash."""
    download_called = []
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: download_called.append(True),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("nonexistent-skill-xyz")
    assert download_called == []


def test_skill_adopt_agora_offline(isolated_skills, monkeypatch):
    """Agora returns None → error message, no crash."""
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")  # must not raise


def test_skill_adopt_network_error_on_download(isolated_skills, monkeypatch):
    """urlopen raises during download → graceful error, no crash, no file created."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("Network error")),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")  # must not raise
    assert not (skills_dir / "daily-planner" / "SKILL.md").exists()


def test_skill_adopt_civic_hash_mismatch_aborts(isolated_skills, monkeypatch):
    """Tampered content (wrong civic hash) → rejected, SKILL.md not written."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    # Return content that does NOT match the registered civic_hash
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: _FakeResponse(b"tampered content that will fail hash check"),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    assert not (skills_dir / "daily-planner" / "SKILL.md").exists()
