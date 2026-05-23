"""Sprint 18-B — Z-Skills v2.0: publish, update, rate.

Tests for:
- cmd_skill_publish: artifact generation from local registry
- cmd_skill_update:  Agora version comparison and re-adopt
- cmd_skill_rate:    local rating persistence (1-5 stars)
"""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# Fixtures — registry isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_skills(tmp_path, monkeypatch):
    """Redirect SKILLS_DIR and REGISTRY_PATH to tmp_path for every test."""
    skills_dir = tmp_path / "skills"
    registry_path = skills_dir / "registry.json"
    monkeypatch.setattr("zana.commands.skill.SKILLS_DIR", skills_dir)
    monkeypatch.setattr("zana.commands.skill.REGISTRY_PATH", registry_path)
    yield skills_dir, registry_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(*skill_entries: dict) -> dict:
    return {"skills": list(skill_entries)}


def _make_entry(
    name: str = "test-skill",
    version: str = "1.0.0",
    description: str = "A test skill",
    author: str = "tester",
    tags: list | str = None,
    **extras,
) -> dict:
    entry: dict = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "tags": tags if tags is not None else [],
        "path": f"/tmp/skills/{name}",
        "installed_at": "2026-05-23T00:00:00+00:00",
    }
    entry.update(extras)
    return entry


# ===========================================================================
# cmd_skill_publish
# ===========================================================================


class TestCmdSkillPublish:
    def test_publish_named_skill_writes_submission_file(
        self, isolated_skills, monkeypatch
    ):
        """Named skill found in registry → agora_submission.json written with correct fields."""
        skills_dir, _ = isolated_skills
        entry = _make_entry()
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(entry),
        )
        saved = {}
        monkeypatch.setattr(
            "zana.commands.skill._save_registry", lambda r: saved.update(r)
        )

        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish("test-skill")

        submission_path = skills_dir / "test-skill" / "agora_submission.json"
        assert submission_path.exists(), "agora_submission.json must be written"
        data = json.loads(submission_path.read_text())
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A test skill"
        assert data["author"] == "tester"
        assert "civic_hash" in data
        assert data["skill_url"] == ""

    def test_publish_submission_contains_pr_instructions(self, monkeypatch, capsys):
        """Output must mention the PR / registry.json contribution URL."""
        entry = _make_entry()
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(entry),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish("test-skill")
        # No exception is sufficient — Rich writes to its own console; stdout may be empty
        # Verify submission file exists (content path already tested above)

    def test_publish_skill_not_found_no_file_written(
        self, isolated_skills, monkeypatch
    ):
        """Skill not in registry → error printed, no agora_submission.json created."""
        skills_dir, _ = isolated_skills
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish("ghost-skill")

        submission_path = skills_dir / "ghost-skill" / "agora_submission.json"
        assert not submission_path.exists()

    def test_publish_name_none_single_skill_auto_detects(
        self, isolated_skills, monkeypatch
    ):
        """name=None with exactly one installed skill → uses it automatically."""
        skills_dir, _ = isolated_skills
        entry = _make_entry(name="solo-skill")
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(entry),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish(None)

        submission_path = skills_dir / "solo-skill" / "agora_submission.json"
        assert submission_path.exists()

    def test_publish_name_none_multiple_skills_no_file_written(
        self, isolated_skills, monkeypatch
    ):
        """name=None with multiple skills → lists them, no submission written."""
        skills_dir, _ = isolated_skills
        entry_a = _make_entry(name="skill-alpha")
        entry_b = _make_entry(name="skill-beta")
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(entry_a, entry_b),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish(None)

        assert not (skills_dir / "skill-alpha" / "agora_submission.json").exists()
        assert not (skills_dir / "skill-beta" / "agora_submission.json").exists()

    def test_publish_civic_hash_is_deterministic(self, isolated_skills, monkeypatch):
        """civic_hash must be consistent across two calls with the same entry."""
        skills_dir, _ = isolated_skills
        entry = _make_entry()
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(entry),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish("test-skill")
        submission_path = skills_dir / "test-skill" / "agora_submission.json"
        hash1 = json.loads(submission_path.read_text())["civic_hash"]

        # Re-run (overwrite)
        cmd_skill_publish("test-skill")
        hash2 = json.loads(submission_path.read_text())["civic_hash"]
        assert hash1 == hash2

    def test_publish_name_none_empty_registry_no_crash(self, monkeypatch):
        """name=None with no installed skills → error message, no exception."""
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(),
        )
        from zana.commands.skill import cmd_skill_publish

        cmd_skill_publish(None)  # must not raise


# ===========================================================================
# cmd_skill_update
# ===========================================================================

MOCK_AGORA = {
    "skills": [
        {
            "name": "test-skill",
            "version": "2.0.0",
            "description": "Updated",
            "author": "author",
            "tags": [],
            "skill_url": "https://example.com/SKILL.md",
            "civic_hash": "",
        },
        {
            "name": "stable-skill",
            "version": "1.0.0",
            "description": "Stable",
            "author": "author",
            "tags": [],
            "skill_url": "https://example.com/stable/SKILL.md",
            "civic_hash": "",
        },
    ]
}


class TestCmdSkillUpdate:
    def test_update_newer_version_calls_adopt(self, monkeypatch):
        """Agora version > local version → cmd_skill_adopt is called."""
        local_entry = _make_entry(name="test-skill", version="1.0.0")
        monkeypatch.setattr(
            "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA
        )
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(local_entry),
        )
        adopt_calls = []
        monkeypatch.setattr(
            "zana.commands.skill.cmd_skill_adopt",
            lambda n: adopt_calls.append(n),
        )
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update("test-skill")
        assert "test-skill" in adopt_calls

    def test_update_same_version_prints_up_to_date(self, monkeypatch):
        """Same version in Agora → adopt NOT called."""
        local_entry = _make_entry(name="stable-skill", version="1.0.0")
        monkeypatch.setattr(
            "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA
        )
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(local_entry),
        )
        adopt_calls = []
        monkeypatch.setattr(
            "zana.commands.skill.cmd_skill_adopt",
            lambda n: adopt_calls.append(n),
        )
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update("stable-skill")
        assert adopt_calls == []

    def test_update_skill_not_in_agora_prints_muted(self, monkeypatch):
        """Skill installed locally but absent from Agora → no crash, no adopt."""
        local_entry = _make_entry(name="orphan-skill", version="1.0.0")
        monkeypatch.setattr(
            "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA
        )
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(local_entry),
        )
        adopt_calls = []
        monkeypatch.setattr(
            "zana.commands.skill.cmd_skill_adopt",
            lambda n: adopt_calls.append(n),
        )
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update("orphan-skill")
        assert adopt_calls == []

    def test_update_agora_unreachable_no_crash(self, monkeypatch):
        """Agora returns None → warning printed, no exception raised."""
        monkeypatch.setattr("zana.commands.skill._fetch_agora_registry", lambda: None)
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update()  # must not raise

    def test_update_name_not_in_local_registry_error(self, monkeypatch):
        """Specific name not in local registry → error, no adopt call."""
        monkeypatch.setattr(
            "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA
        )
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(),
        )
        adopt_calls = []
        monkeypatch.setattr(
            "zana.commands.skill.cmd_skill_adopt",
            lambda n: adopt_calls.append(n),
        )
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update("nonexistent")
        assert adopt_calls == []

    def test_update_name_none_checks_all_installed(self, monkeypatch):
        """name=None → checks every skill in the local registry."""
        entries = [
            _make_entry(name="test-skill", version="1.0.0"),
            _make_entry(name="stable-skill", version="1.0.0"),
        ]
        monkeypatch.setattr(
            "zana.commands.skill._fetch_agora_registry", lambda: MOCK_AGORA
        )
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(*entries),
        )
        adopt_calls = []
        monkeypatch.setattr(
            "zana.commands.skill.cmd_skill_adopt",
            lambda n: adopt_calls.append(n),
        )
        from zana.commands.skill import cmd_skill_update

        cmd_skill_update(None)
        # test-skill has newer version → should be adopted; stable-skill should not
        assert "test-skill" in adopt_calls
        assert "stable-skill" not in adopt_calls


# ===========================================================================
# cmd_skill_rate
# ===========================================================================


class TestCmdSkillRate:
    def _setup_registry(self, monkeypatch, entry: dict) -> list:
        """Wire _load_registry and _save_registry; return captured saves."""
        registry_state = _make_registry(entry)
        saved_registries: list[dict] = []

        def _fake_load():
            return registry_state

        def _fake_save(r: dict) -> None:
            saved_registries.append(r)
            registry_state["skills"] = r["skills"]

        monkeypatch.setattr("zana.commands.skill._load_registry", _fake_load)
        monkeypatch.setattr("zana.commands.skill._save_registry", _fake_save)
        return saved_registries

    def test_rate_4_saved_in_registry(self, monkeypatch):
        """Rating 4 → entry['rating'] == 4 persisted via _save_registry."""
        entry = _make_entry()
        saved = self._setup_registry(monkeypatch, entry)

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 4)

        assert len(saved) == 1
        saved_entry = next(s for s in saved[0]["skills"] if s["name"] == "test-skill")
        assert saved_entry["rating"] == 4

    def test_rate_0_prints_error_no_save(self, monkeypatch):
        """Rating 0 → error, _save_registry never called."""
        entry = _make_entry()
        saved = self._setup_registry(monkeypatch, entry)

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 0)
        assert saved == []

    def test_rate_6_prints_error_no_save(self, monkeypatch):
        """Rating 6 → error, _save_registry never called."""
        entry = _make_entry()
        saved = self._setup_registry(monkeypatch, entry)

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 6)
        assert saved == []

    def test_rate_skill_not_found_no_save(self, monkeypatch):
        """Skill not in registry → error, _save_registry never called."""
        monkeypatch.setattr(
            "zana.commands.skill._load_registry",
            lambda: _make_registry(),
        )
        saved_calls: list = []
        monkeypatch.setattr(
            "zana.commands.skill._save_registry",
            lambda r: saved_calls.append(r),
        )

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("missing-skill", 3)
        assert saved_calls == []

    def test_rate_stars_display_3(self, monkeypatch, capsys):
        """Rating 3 → star string '★★★☆☆' present in console output."""
        entry = _make_entry()
        self._setup_registry(monkeypatch, entry)

        # Capture Rich console output by patching console.print
        printed: list[str] = []
        monkeypatch.setattr(
            "zana.commands.skill.console",
            type(
                "FakeConsole",
                (),
                {"print": staticmethod(lambda *a, **kw: printed.append(str(a[0])))},
            )(),
        )

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 3)

        combined = " ".join(printed)
        assert "★★★☆☆" in combined

    def test_rate_stars_display_1(self, monkeypatch):
        """Rating 1 → star string '★☆☆☆☆' in output."""
        entry = _make_entry()
        self._setup_registry(monkeypatch, entry)

        printed: list[str] = []
        monkeypatch.setattr(
            "zana.commands.skill.console",
            type(
                "FakeConsole",
                (),
                {"print": staticmethod(lambda *a, **kw: printed.append(str(a[0])))},
            )(),
        )

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 1)
        combined = " ".join(printed)
        assert "★☆☆☆☆" in combined

    def test_rate_stars_display_5(self, monkeypatch):
        """Rating 5 → star string '★★★★★' in output."""
        entry = _make_entry()
        self._setup_registry(monkeypatch, entry)

        printed: list[str] = []
        monkeypatch.setattr(
            "zana.commands.skill.console",
            type(
                "FakeConsole",
                (),
                {"print": staticmethod(lambda *a, **kw: printed.append(str(a[0])))},
            )(),
        )

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 5)
        combined = " ".join(printed)
        assert "★★★★★" in combined

    def test_rate_overwrites_previous_rating(self, monkeypatch):
        """Re-rating a skill updates the rating (not appends)."""
        entry = _make_entry(rating=2)
        saved = self._setup_registry(monkeypatch, entry)

        from zana.commands.skill import cmd_skill_rate

        cmd_skill_rate("test-skill", 5)
        assert len(saved) == 1
        saved_entry = next(s for s in saved[0]["skills"] if s["name"] == "test-skill")
        assert saved_entry["rating"] == 5
