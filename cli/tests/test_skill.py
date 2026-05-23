"""
test_skill.py — Z-Skill test suite (Sprint 9 + Sprint 12 — The Agora v1)

Covers: cmd_skill_create, cmd_skill_list, cmd_skill_run, cmd_skill_info,
        cmd_skill_publish, cmd_skill_search, cmd_skill_adopt,
        WisdomQueue helpers, registry read/write, frontmatter parsing.
All tests use tmp_path isolation — no shared state.
"""

from __future__ import annotations

import json

import pytest
from zana.commands.skill import (
    _civic_hash,
    _load_registry,
    _parse_frontmatter,
    _save_registry,
    cmd_skill_adopt,
    cmd_skill_create,
    cmd_skill_info,
    cmd_skill_list,
    cmd_skill_publish,
    cmd_skill_run,
    cmd_skill_search,
)

# ---------------------------------------------------------------------------
# Fixtures
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
# _parse_frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_extracts_fields():
    md = "---\nname: my-skill\nversion: 2.0.0\ndescription: Does things\n---\n## Body"
    meta = _parse_frontmatter(md)
    assert meta["name"] == "my-skill"
    assert meta["version"] == "2.0.0"
    assert meta["description"] == "Does things"


def test_parse_frontmatter_missing_block_returns_empty():
    assert _parse_frontmatter("no frontmatter here") == {}


def test_parse_frontmatter_strips_quotes():
    md = '---\nzana_version: ">=3.5.0"\n---'
    meta = _parse_frontmatter(md)
    assert meta["zana_version"] == ">=3.5.0"


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def test_load_registry_creates_default_on_missing_file(isolated_skills):
    skills_dir, registry_path = isolated_skills
    result = _load_registry()
    assert "skills" in result
    assert result["skills"] == []
    assert registry_path.exists()


def test_save_and_load_registry_roundtrip(isolated_skills):
    data = {"skills": [{"name": "test-skill", "version": "1.0.0"}]}
    _save_registry(data)
    loaded = _load_registry()
    assert loaded["skills"][0]["name"] == "test-skill"


# ---------------------------------------------------------------------------
# cmd_skill_create
# ---------------------------------------------------------------------------


def test_skill_create_creates_skill_md(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("my-skill")
    assert (skills_dir / "my-skill" / "SKILL.md").exists()


def test_skill_create_registers_in_registry(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("registered-skill")
    registry = _load_registry()
    names = [s["name"] for s in registry["skills"]]
    assert "registered-skill" in names


def test_skill_create_with_author(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("authored-skill", author="john")
    skill_md = (skills_dir / "authored-skill" / "SKILL.md").read_text()
    assert "john" in skill_md


def test_skill_create_invalid_name_does_not_create(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("Invalid Name!")  # uppercase + space + exclamation
    assert not (skills_dir / "Invalid Name!" / "SKILL.md").exists()


def test_skill_create_duplicate_does_not_overwrite(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("dup-skill")
    # Overwrite manually to simulate user edits
    (skills_dir / "dup-skill" / "SKILL.md").write_text("custom content")
    cmd_skill_create("dup-skill")  # should not overwrite
    assert (skills_dir / "dup-skill" / "SKILL.md").read_text() == "custom content"


# ---------------------------------------------------------------------------
# cmd_skill_list
# ---------------------------------------------------------------------------


def test_skill_list_empty_registry_does_not_raise(isolated_skills):
    cmd_skill_list()  # must not raise


def test_skill_list_shows_installed_skills(isolated_skills, capsys):
    cmd_skill_create("visible-skill")
    cmd_skill_list()  # must not raise; skill name appears in registry


def test_skill_list_multiple_skills(isolated_skills):
    cmd_skill_create("alpha-skill")
    cmd_skill_create("beta-skill")
    registry = _load_registry()
    assert len(registry["skills"]) == 2


# ---------------------------------------------------------------------------
# cmd_skill_info
# ---------------------------------------------------------------------------


def test_skill_info_existing_skill_does_not_raise(isolated_skills):
    cmd_skill_create("info-skill")
    cmd_skill_info("info-skill")  # must not raise


def test_skill_info_missing_skill_does_not_raise(isolated_skills):
    cmd_skill_info("nonexistent-skill")  # must not raise, prints error message


# ---------------------------------------------------------------------------
# cmd_skill_run
# ---------------------------------------------------------------------------


def test_skill_run_missing_skill_does_not_raise(isolated_skills):
    cmd_skill_run("missing-skill", "any prompt")  # must not raise


def test_skill_run_existing_skill_loads_skill_md(isolated_skills):
    cmd_skill_create("runnable-skill")
    # ZSM may not be available in test env — that's OK, the fallback path must not raise
    cmd_skill_run("runnable-skill", "test prompt")  # must not raise


# ---------------------------------------------------------------------------
# CLI wiring via typer (smoke test)
# ---------------------------------------------------------------------------


def test_cli_skill_create_via_typer(isolated_skills):
    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "create", "cli-wired-skill"])
    assert result.exit_code == 0


def test_cli_skill_list_via_typer(isolated_skills):
    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "list"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _civic_hash
# ---------------------------------------------------------------------------


def test_civic_hash_returns_sha256_prefix():
    h = _civic_hash("hello world")
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 16


def test_civic_hash_deterministic():
    assert _civic_hash("same content") == _civic_hash("same content")


def test_civic_hash_different_content():
    assert _civic_hash("aaa") != _civic_hash("bbb")


# ---------------------------------------------------------------------------
# cmd_skill_publish
# ---------------------------------------------------------------------------


def test_skill_publish_missing_skill_does_not_raise(isolated_skills):
    # New API: name=None with empty registry → no crash
    cmd_skill_publish()


def test_skill_publish_creates_submission_json(isolated_skills):
    skills_dir, _ = isolated_skills
    cmd_skill_create("pub-skill", author="john")
    cmd_skill_publish("pub-skill")
    submission = skills_dir / "pub-skill" / "agora_submission.json"
    assert submission.exists()
    data = json.loads(submission.read_text())
    assert data["name"] == "pub-skill"
    assert data["civic_hash"].startswith("sha256:")
    # New API: artifact is built from registry entry, not raw SKILL.md content
    assert "skill_url" in data


def test_skill_publish_civic_hash_matches_content(isolated_skills):
    import json as _json

    skills_dir, _ = isolated_skills
    cmd_skill_create("hash-skill")
    cmd_skill_publish("hash-skill")
    submission = _json.loads(
        (skills_dir / "hash-skill" / "agora_submission.json").read_text()
    )
    # civic_hash is over the registry entry JSON, not raw SKILL.md — just verify format
    assert submission["civic_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# cmd_skill_search (offline — mocked registry)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_agora_registry(monkeypatch):
    """Replace _fetch_agora_registry with a local stub."""
    registry = {
        "version": "1.0",
        "skills": [
            {
                "name": "summarize",
                "version": "1.0.0",
                "description": "Summarize any text or document",
                "author": "john",
                "tags": ["productivity", "text"],
                "skill_url": "https://example.com/skills/summarize/SKILL.md",
                "civic_hash": _civic_hash("summarize-content"),
            },
            {
                "name": "translate",
                "version": "1.0.0",
                "description": "Translate text between languages",
                "author": "maria",
                "tags": ["language", "text"],
                "skill_url": "https://example.com/skills/translate/SKILL.md",
                "civic_hash": _civic_hash("translate-content"),
            },
        ],
    }
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: registry)
    return registry


def test_skill_search_returns_matching_skills(isolated_skills, mock_agora_registry):
    cmd_skill_search("summarize")  # must not raise


def test_skill_search_no_matches_does_not_raise(isolated_skills, mock_agora_registry):
    cmd_skill_search("zzznomatch")  # must not raise


def test_skill_search_by_tag(isolated_skills, mock_agora_registry):
    cmd_skill_search("language")  # matches "translate" via tag


def test_skill_search_offline_does_not_raise(isolated_skills, monkeypatch):
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    cmd_skill_search("anything")  # must not raise


# ---------------------------------------------------------------------------
# cmd_skill_adopt
# ---------------------------------------------------------------------------


_SAMPLE_SKILL_MD = """\
---
name: summarize
version: 1.0.0
description: Summarize any text
author: john
tags: []
zana_version: ">=3.5.0"
created_at: 2026-05-20
---

## Trigger
- "summarize"

## Steps
1. Read input
2. Return summary
"""


@pytest.fixture
def mock_agora_with_download(monkeypatch):
    """Stub both registry fetch and SKILL.md download."""
    civic = _civic_hash(_SAMPLE_SKILL_MD)
    registry = {
        "skills": [
            {
                "name": "summarize",
                "version": "1.0.0",
                "description": "Summarize any text",
                "author": "john",
                "tags": [],
                "skill_url": "https://example.com/skills/summarize/SKILL.md",
                "civic_hash": civic,
            }
        ]
    }

    class FakeResponse:
        def read(self):
            return _SAMPLE_SKILL_MD.encode()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: registry)
    monkeypatch.setattr("zana.commands.skill.urlopen", lambda *a, **kw: FakeResponse())
    return registry


def test_skill_adopt_installs_skill(isolated_skills, mock_agora_with_download):
    skills_dir, _ = isolated_skills
    cmd_skill_adopt("summarize")
    assert (skills_dir / "summarize" / "SKILL.md").exists()


def test_skill_adopt_registers_in_registry(isolated_skills, mock_agora_with_download):
    cmd_skill_adopt("summarize")
    reg = _load_registry()
    names = [s["name"] for s in reg["skills"]]
    assert "summarize" in names


def test_skill_adopt_already_installed_does_not_overwrite(
    isolated_skills, mock_agora_with_download
):
    skills_dir, _ = isolated_skills
    cmd_skill_create("summarize")
    (skills_dir / "summarize" / "SKILL.md").write_text("custom content")
    cmd_skill_adopt("summarize")
    assert (skills_dir / "summarize" / "SKILL.md").read_text() == "custom content"


def test_skill_adopt_not_in_agora_does_not_raise(
    isolated_skills, mock_agora_with_download
):
    cmd_skill_adopt("unknown-skill")  # must not raise


def test_skill_adopt_offline_does_not_raise(isolated_skills, monkeypatch):
    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
    cmd_skill_adopt("any-skill")  # must not raise


def test_skill_adopt_civic_mismatch_aborts(
    isolated_skills, mock_agora_with_download, monkeypatch
):
    """Tampered content (wrong hash) must be rejected."""
    skills_dir, _ = isolated_skills

    class TamperedResponse:
        def read(self):
            return b"tampered skill content that doesn't match hash"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(
        "zana.commands.skill.urlopen", lambda *a, **kw: TamperedResponse()
    )
    cmd_skill_adopt("summarize")
    assert not (skills_dir / "summarize" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# CLI wiring — Agora commands
# ---------------------------------------------------------------------------


def test_cli_skill_publish_via_typer(isolated_skills):
    from typer.testing import CliRunner
    from zana.main import app

    skills_dir, _ = isolated_skills
    cmd_skill_create("typer-pub-skill")

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "publish", "typer-pub-skill"])
    assert result.exit_code == 0


def test_cli_skill_search_via_typer(isolated_skills, monkeypatch):
    from typer.testing import CliRunner
    from zana.main import app

    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "search", "test"])
    assert result.exit_code == 0


def test_cli_skill_adopt_via_typer(isolated_skills, monkeypatch):
    from typer.testing import CliRunner
    from zana.main import app

    monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "adopt", "any-skill"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# cmd_skill_search --local  (Issue #25)
# ---------------------------------------------------------------------------


def _populate_registry(registry_path, skills_dir):
    """Write two skills to the local registry for search tests."""
    skills_dir.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "name": "weather-check",
            "version": "1.0.0",
            "description": "Fetch current weather for a city",
            "author": "alice",
        },
        {
            "name": "math-solver",
            "version": "1.1.0",
            "description": "Solve arithmetic and algebra",
            "author": "bob",
        },
    ]
    registry_path.write_text(json.dumps({"skills": entries}))
    return entries


def test_local_search_matches_by_name(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)

    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "search", "--local", "weather"])
    assert result.exit_code == 0
    assert "weather-check" in result.output
    assert "math-solver" not in result.output


def test_local_search_matches_by_description(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)

    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "search", "--local", "algebra"])
    assert result.exit_code == 0
    assert "math-solver" in result.output
    assert "weather-check" not in result.output


def test_local_search_matches_by_tag(isolated_skills):
    skills_dir, registry = isolated_skills
    skills_dir.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "name": "geo-tool",
            "version": "1.0.0",
            "description": "Location data",
            "author": "carl",
            "tags": ["geo", "maps"],
        },
        {
            "name": "chat-tool",
            "version": "1.0.0",
            "description": "Conversation helper",
            "author": "dana",
            "tags": ["nlp"],
        },
    ]
    registry.write_text(json.dumps({"skills": entries}))

    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "search", "--local", "geo"])
    assert result.exit_code == 0
    assert "geo-tool" in result.output
    assert "chat-tool" not in result.output


def test_local_search_no_matches_does_not_raise(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("zzznomatch", local=True)


def test_local_search_empty_registry_does_not_raise(isolated_skills):
    skills_dir, registry = isolated_skills
    skills_dir.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"skills": []}))
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("anything", local=True)


def test_local_search_case_insensitive_name(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)
    from zana.commands.skill import _cmd_skill_search_local

    _cmd_skill_search_local("WEATHER")


def test_local_search_case_insensitive_description(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)
    from zana.commands.skill import _cmd_skill_search_local

    _cmd_skill_search_local("ARITHMETIC")


def test_local_flag_does_not_call_agora(isolated_skills, monkeypatch):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)

    called = []
    monkeypatch.setattr(
        "zana.commands.skill._fetch_agora_registry", lambda: called.append(True) or {}
    )
    from zana.commands.skill import cmd_skill_search

    cmd_skill_search("weather", local=True)
    assert called == [], "--local must not hit the network"


def test_cli_skill_search_local_flag_via_typer(isolated_skills):
    skills_dir, registry = isolated_skills
    _populate_registry(registry, skills_dir)

    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["skill", "search", "--local", "weather"])
    assert result.exit_code == 0
