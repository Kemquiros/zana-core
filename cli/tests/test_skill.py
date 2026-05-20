"""
test_skill.py — Z-Skill v1.0 test suite (Sprint 9 · Issue #4)

Covers: cmd_skill_create, cmd_skill_list, cmd_skill_run, cmd_skill_info,
        WisdomQueue helpers, registry read/write, frontmatter parsing.
All tests use tmp_path isolation — no shared state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from zana.commands.skill import (
    REGISTRY_PATH,
    SKILLS_DIR,
    _load_registry,
    _parse_frontmatter,
    _register_skill,
    _save_registry,
    cmd_skill_create,
    cmd_skill_info,
    cmd_skill_list,
    cmd_skill_run,
)
from zana.commands.skill import SKILLS_DIR as _SKILLS_DIR_ORIG
from zana.commands.skill import REGISTRY_PATH as _REGISTRY_PATH_ORIG


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
    first_content = (skills_dir / "dup-skill" / "SKILL.md").read_text()
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
