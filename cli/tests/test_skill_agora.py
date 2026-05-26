"""Tests for The Agora v1.0 — Skill Marketplace.

Covers:
  - agora.py core module: fetch_registry, search_registry, pack_skill,
    publish_skill_to_agora, install_skill_from_agora
  - skill.py Agora commands: cmd_skill_publish_agora, cmd_skill_search (--agora),
    cmd_skill_adopt (agora path)

All network calls are mocked. No real HTTP requests are made.
Uses tmp_path for all file operations.
"""

from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import patch

import pytest
from zana.commands.skill import _civic_hash
from zana.core import agora

# ---------------------------------------------------------------------------
# Fixtures — registry isolation
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
# Shared fixtures
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

MOCK_REGISTRY_LIST = [
    {
        "id": "daily-planner",
        "name": "daily-planner",
        "description": "Helps organize daily tasks and priorities",
        "version": "1.0.0",
        "author": "JohnDoe",
        "tags": ["productivity", "planning"],
        "skill_url": "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/skills/daily-planner/SKILL.md",
        "civic_hash": _civic_hash(MOCK_SKILL_CONTENT),
    },
    {
        "id": "recipe-finder",
        "name": "recipe-finder",
        "description": "Find recipes based on available ingredients",
        "version": "1.2.0",
        "author": "CookBot",
        "tags": ["cooking", "recipes"],
        "skill_url": "https://raw.githubusercontent.com/Kemquiros/zana-agora/main/skills/recipe-finder/SKILL.md",
        "civic_hash": "sha256:abcdefabcdef1234",
    },
]

MOCK_AGORA_REGISTRY = {
    "version": "1.0",
    "skills": MOCK_REGISTRY_LIST,
}


class _FakeResponse:
    """Minimal context-manager response for urllib.request.urlopen mocking."""

    def __init__(self, content: bytes, status: int = 200):
        self._content = content
        self.status = status

    def read(self) -> bytes:
        return self._content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


# ---------------------------------------------------------------------------
# 1. test_fetch_registry_success — mock urllib response
# ---------------------------------------------------------------------------


def test_fetch_registry_success():
    """fetch_registry() returns parsed list on successful HTTP response."""
    payload = json.dumps(MOCK_AGORA_REGISTRY).encode()
    with patch("zana.core.agora.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _FakeResponse(payload)
        result = agora.fetch_registry()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "daily-planner"


# ---------------------------------------------------------------------------
# 2. test_fetch_registry_network_error — returns []
# ---------------------------------------------------------------------------


def test_fetch_registry_network_error():
    """fetch_registry() returns [] on network failure (URLError)."""
    import urllib.error

    with patch("zana.core.agora.urllib.request.urlopen") as mock_open:
        mock_open.side_effect = urllib.error.URLError("connection refused")
        result = agora.fetch_registry()
    assert result == []


# ---------------------------------------------------------------------------
# 3. test_search_registry_by_name
# ---------------------------------------------------------------------------


def test_search_registry_by_name():
    """search_registry filters by name match."""
    results = agora.search_registry("daily", MOCK_REGISTRY_LIST)
    assert len(results) == 1
    assert results[0]["name"] == "daily-planner"


# ---------------------------------------------------------------------------
# 4. test_search_registry_by_tag
# ---------------------------------------------------------------------------


def test_search_registry_by_tag():
    """search_registry filters by tag match."""
    results = agora.search_registry("cooking", MOCK_REGISTRY_LIST)
    assert len(results) == 1
    assert results[0]["name"] == "recipe-finder"


# ---------------------------------------------------------------------------
# 5. test_search_registry_empty_query
# ---------------------------------------------------------------------------


def test_search_registry_empty_query():
    """search_registry with empty query returns all entries."""
    results = agora.search_registry("", MOCK_REGISTRY_LIST)
    assert len(results) == len(MOCK_REGISTRY_LIST)


# ---------------------------------------------------------------------------
# 6. test_pack_skill_creates_zip — use tmp_path
# ---------------------------------------------------------------------------


def test_pack_skill_creates_zip(tmp_path):
    """pack_skill() returns valid zip bytes containing SKILL.md."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(MOCK_SKILL_CONTENT)
    (skill_dir / "helper.txt").write_text("extra file")

    result = agora.pack_skill(skill_dir)

    assert isinstance(result, bytes)
    assert len(result) > 0
    # Verify it is a valid zip
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert "SKILL.md" in names
    assert "helper.txt" in names


# ---------------------------------------------------------------------------
# 7. test_pack_skill_missing_skill_md — raises FileNotFoundError
# ---------------------------------------------------------------------------


def test_pack_skill_missing_skill_md(tmp_path):
    """pack_skill() raises FileNotFoundError when SKILL.md is absent."""
    skill_dir = tmp_path / "empty-skill"
    skill_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="SKILL.md"):
        agora.pack_skill(skill_dir)


# ---------------------------------------------------------------------------
# 8. test_publish_skill_to_agora_success — mock urllib, check issue URL
# ---------------------------------------------------------------------------


def test_publish_skill_to_agora_success(tmp_path):
    """publish_skill_to_agora() returns issue URL on successful API call."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(MOCK_SKILL_CONTENT)

    api_response = json.dumps(
        {"html_url": "https://github.com/Kemquiros/zana-agora/issues/42"}
    ).encode()

    with patch("zana.core.agora.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _FakeResponse(api_response)
        url = agora.publish_skill_to_agora("my-skill", skill_dir, "ghp_faketoken123")

    assert url == "https://github.com/Kemquiros/zana-agora/issues/42"
    mock_open.assert_called_once()


# ---------------------------------------------------------------------------
# 9. test_publish_skill_to_agora_no_token — raises ValueError
# ---------------------------------------------------------------------------


def test_publish_skill_to_agora_no_token(tmp_path):
    """publish_skill_to_agora() raises ValueError when token is empty."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(MOCK_SKILL_CONTENT)

    with pytest.raises(ValueError, match="token"):
        agora.publish_skill_to_agora("my-skill", skill_dir, "")

    with pytest.raises(ValueError, match="token"):
        agora.publish_skill_to_agora("my-skill", skill_dir, "   ")


# ---------------------------------------------------------------------------
# 10. test_cmd_skill_publish_agora_smoke — mock agora module
# ---------------------------------------------------------------------------


def test_cmd_skill_publish_agora_smoke(isolated_skills, monkeypatch):
    """cmd_skill_publish_agora runs without error when agora module is mocked."""
    skills_dir, _ = isolated_skills

    # Create a real skill on disk
    skill_dir = skills_dir / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(MOCK_SKILL_CONTENT)

    monkeypatch.setattr(
        "zana.commands.skill.agora_module.pack_skill",
        lambda d: b"fake-zip-bytes",
    )
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.publish_skill_to_agora",
        lambda name, d, token: "https://github.com/Kemquiros/zana-agora/issues/99",
    )

    from zana.commands.skill import cmd_skill_publish_agora

    cmd_skill_publish_agora("my-skill", github_token="ghp_testtoken")  # must not raise


# ---------------------------------------------------------------------------
# 11. test_cmd_skill_search_agora_smoke — mock fetch_registry
# ---------------------------------------------------------------------------


def test_cmd_skill_search_agora_smoke(monkeypatch):
    """cmd_skill_search with agora=True fetches registry and renders table."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )

    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity", agora=True)  # must not raise


# ---------------------------------------------------------------------------
# 12. test_cmd_skill_adopt_smoke — mock fetch_registry + urlopen
# ---------------------------------------------------------------------------


def test_cmd_skill_adopt_smoke(isolated_skills, monkeypatch):
    """cmd_skill_adopt downloads and registers a skill without error."""
    skills_dir, _ = isolated_skills

    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: _FakeResponse(MOCK_SKILL_CONTENT.encode()),
    )

    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    assert (skills_dir / "daily-planner" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# 13. test_install_skill_from_agora_smoke — mock urllib download + tmp_path
# ---------------------------------------------------------------------------


def test_install_skill_from_agora_smoke(tmp_path):
    """install_skill_from_agora extracts SKILL.md to target directory."""
    with patch("zana.core.agora.urllib.request.urlopen") as mock_open:
        # First call: registry fetch
        registry_payload = json.dumps(MOCK_AGORA_REGISTRY).encode()
        # Second call: skill download
        skill_payload = MOCK_SKILL_CONTENT.encode()
        mock_open.side_effect = [
            _FakeResponse(registry_payload),
            _FakeResponse(skill_payload),
        ]

        result = agora.install_skill_from_agora("daily-planner", tmp_path)

    assert result == tmp_path / "daily-planner"
    assert (result / "SKILL.md").exists()
    assert (result / "SKILL.md").read_text(encoding="utf-8") == MOCK_SKILL_CONTENT


# ---------------------------------------------------------------------------
# 14. test_search_registry_case_insensitive
# ---------------------------------------------------------------------------


def test_search_registry_case_insensitive():
    """search_registry treats query and fields as case-insensitive."""
    # Uppercase query matching lowercase field
    results = agora.search_registry("DAILY", MOCK_REGISTRY_LIST)
    assert any(r["name"] == "daily-planner" for r in results)

    # Mixed case tag match
    results = agora.search_registry("Productivity", MOCK_REGISTRY_LIST)
    assert any(r["name"] == "daily-planner" for r in results)

    # Description search case-insensitive
    results = agora.search_registry("ORGANIZE", MOCK_REGISTRY_LIST)
    assert any(r["name"] == "daily-planner" for r in results)


# ---------------------------------------------------------------------------
# 15. test_fetch_registry_invalid_json — returns []
# ---------------------------------------------------------------------------


def test_fetch_registry_invalid_json():
    """fetch_registry() returns [] when response contains invalid JSON."""
    with patch("zana.core.agora.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _FakeResponse(b"this is not json {{{{")
        result = agora.fetch_registry()
    assert result == []


# ---------------------------------------------------------------------------
# Legacy test_skill_agora.py tests (preserved for regression coverage)
# ---------------------------------------------------------------------------


def test_skill_search_remote_returns_matches(monkeypatch):
    """Agora registry with matching skills renders without error."""
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA_REGISTRY
    )
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity")  # must not raise


def test_skill_search_remote_match_by_name(monkeypatch):
    """Query matching skill name produces no exception."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("daily-planner")  # must not raise


def test_skill_search_remote_match_by_tag(monkeypatch):
    """Query matching a tag produces no exception."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("cooking")  # matches recipe-finder via tag


def test_skill_search_remote_no_results(monkeypatch):
    """Query with no remote matches prints helpful message without crashing."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("quantum_cooking_blockchain")  # clearly no match


def test_skill_search_falls_back_gracefully_when_offline(monkeypatch):
    """Agora returns [] (offline) -> warning is printed, no exception raised."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: [],
    )
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity")  # must not raise


def test_skill_search_local_flag_does_not_hit_agora(monkeypatch):
    """--local flag must never call agora_module.fetch_registry."""
    called = []
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: called.append(True) or [],
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("productivity", local=True)
    assert called == [], "--local must not hit the network"


def test_skill_adopt_success(isolated_skills, monkeypatch):
    """Valid skill in Agora -> SKILL.md written to ~/.zana/skills/<name>/."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
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
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
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
    """Skill SKILL.md already present -> warning shown, urlopen never called."""
    skills_dir, _ = isolated_skills
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
    assert (skill_dir / "SKILL.md").read_text() == "existing content"


def test_skill_adopt_not_found_in_agora(isolated_skills, monkeypatch):
    """Skill not in remote registry -> error message, no download, no crash."""
    download_called = []
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: download_called.append(True),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("nonexistent-skill-xyz")
    assert download_called == []


def test_skill_adopt_agora_offline(isolated_skills, monkeypatch):
    """Agora returns [] -> fallback to legacy helper -> offline warning, no crash."""
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: [],
    )
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")  # must not raise


def test_skill_adopt_network_error_on_download(isolated_skills, monkeypatch):
    """urlopen raises during download -> graceful error, no crash, no file created."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("Network error")),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")  # must not raise
    assert not (skills_dir / "daily-planner" / "SKILL.md").exists()


def test_skill_adopt_civic_hash_mismatch_aborts(isolated_skills, monkeypatch):
    """Tampered content (wrong civic hash) -> rejected, SKILL.md not written."""
    skills_dir, _ = isolated_skills
    monkeypatch.setattr(
        "zana.commands.skill.agora_module.fetch_registry",
        lambda: MOCK_REGISTRY_LIST,
    )
    monkeypatch.setattr(
        "zana.commands.skill.urlopen",
        lambda *a, **kw: _FakeResponse(b"tampered content that will fail hash check"),
    )
    from zana.commands.skill import cmd_skill_adopt

    cmd_skill_adopt("daily-planner")
    assert not (skills_dir / "daily-planner" / "SKILL.md").exists()
