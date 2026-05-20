"""
test_identity.py — ZANA ID export/import + zaeon:// URI (Sprint 12)

Covers: cmd_id_export, cmd_id_import, cmd_id_zaeon, _encrypt/_decrypt,
        _build_bundle, _restore_bundle, _compute_zaeon_uri.
All tests use tmp_path isolation — no shared ~/.zana state.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from zana.commands.identity import (
    _MAGIC,
    _build_bundle,
    _compute_zaeon_uri,
    _decrypt,
    _derive_key,
    _encrypt,
    _restore_bundle,
    cmd_id_export,
    cmd_id_import,
    cmd_id_zaeon,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_aeon_home(tmp_path, monkeypatch):
    """Redirect AEON_HOME and all derived paths to tmp_path."""
    aeon_home = tmp_path / ".zana"
    aeon_home.mkdir()
    monkeypatch.setattr("zana.commands.identity.AEON_HOME", aeon_home)
    monkeypatch.setattr("zana.tui.aeon_dna.AEON_HOME", aeon_home)
    monkeypatch.setattr(
        "zana.tui.aeon_dna.PROFILE_PATH", aeon_home / "aeon_profile.json"
    )
    monkeypatch.setattr("zana.tui.aeon_dna.DNA_PATH", aeon_home / "aeon_dna.json")
    yield aeon_home


@pytest.fixture
def sample_profile(isolated_aeon_home):
    """Write a minimal aeon_profile.json and aeon_dna.json."""
    profile = {
        "name": "TestAeon",
        "archetype": "warrior",
        "init_at": "2026-05-20",
        "vault_notes": 3,
        "memory_count": 10,
        "ledger_count": 5,
    }
    (isolated_aeon_home / "aeon_profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )
    dna = {"genes": [0.5] * 21, "generation": 1}
    (isolated_aeon_home / "aeon_dna.json").write_text(json.dumps(dna), encoding="utf-8")
    return profile


@pytest.fixture
def sample_skills(isolated_aeon_home):
    """Create a skill in the skills directory."""
    skills_dir = isolated_aeon_home / "skills"
    skills_dir.mkdir()
    (skills_dir / "registry.json").write_text(
        json.dumps({"skills": [{"name": "test-skill"}]}), encoding="utf-8"
    )
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\nversion: 1.0.0\n---\n## Body\n", encoding="utf-8"
    )


@pytest.fixture
def sample_memory(isolated_aeon_home):
    """Create a minimal memory_lite.db."""
    db_path = isolated_aeon_home / "memory_lite.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT)"
    )
    conn.execute("INSERT INTO memories (content) VALUES ('test memory')")
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# _derive_key
# ---------------------------------------------------------------------------


def test_derive_key_is_deterministic():
    salt = b"\x00" * 16
    k1 = _derive_key("passphrase", salt)
    k2 = _derive_key("passphrase", salt)
    assert k1 == k2


def test_derive_key_differs_with_different_salt():
    k1 = _derive_key("passphrase", b"\x00" * 16)
    k2 = _derive_key("passphrase", b"\xff" * 16)
    assert k1 != k2


def test_derive_key_differs_with_different_passphrase():
    salt = b"\x00" * 16
    k1 = _derive_key("passphrase1", salt)
    k2 = _derive_key("passphrase2", salt)
    assert k1 != k2


# ---------------------------------------------------------------------------
# _encrypt / _decrypt roundtrip
# ---------------------------------------------------------------------------


def test_encrypt_starts_with_magic():
    enc = _encrypt(b"hello", "secret")
    assert enc.startswith(_MAGIC)


def test_encrypt_decrypt_roundtrip():
    payload = b"sovereign aeon data"
    enc = _encrypt(payload, "my-passphrase")
    dec = _decrypt(enc, "my-passphrase")
    assert dec == payload


def test_decrypt_wrong_passphrase_raises():
    enc = _encrypt(b"data", "correct")
    with pytest.raises(ValueError, match="Wrong passphrase"):
        _decrypt(enc, "wrong")


def test_decrypt_bad_magic_raises():
    with pytest.raises(ValueError, match="bad magic"):
        _decrypt(b"NOTAEON\x00" + b"\x00" * 50, "anything")


def test_encrypt_different_calls_produce_different_ciphertext():
    enc1 = _encrypt(b"same", "pass")
    enc2 = _encrypt(b"same", "pass")
    assert enc1 != enc2  # different salts → different ciphertext


# ---------------------------------------------------------------------------
# _compute_zaeon_uri
# ---------------------------------------------------------------------------


def test_zaeon_uri_format(sample_profile, isolated_aeon_home):
    uri = _compute_zaeon_uri()
    assert uri.startswith("zaeon://")
    assert "?id=" in uri


def test_zaeon_uri_contains_aeon_name(sample_profile, isolated_aeon_home):
    uri = _compute_zaeon_uri()
    assert "testaeon" in uri


def test_zaeon_uri_is_deterministic(sample_profile, isolated_aeon_home):
    assert _compute_zaeon_uri() == _compute_zaeon_uri()


def test_zaeon_uri_no_profile_returns_unknown(isolated_aeon_home):
    uri = _compute_zaeon_uri()
    assert "unknown" in uri


# ---------------------------------------------------------------------------
# _build_bundle
# ---------------------------------------------------------------------------


def test_build_bundle_contains_exported_at(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert "exported_at" in b


def test_build_bundle_contains_profile(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert "aeon_profile" in b
    assert b["aeon_profile"]["name"] == "TestAeon"


def test_build_bundle_contains_dna(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert "aeon_dna" in b


def test_build_bundle_contains_skills(
    sample_profile, sample_skills, isolated_aeon_home
):
    b = _build_bundle()
    assert "skills_registry" in b
    assert "test-skill" in b.get("skill_files", {})


def test_build_bundle_contains_memory_sql(
    sample_profile, sample_memory, isolated_aeon_home
):
    b = _build_bundle()
    assert "memory_sql" in b
    assert "memories" in b["memory_sql"]


def test_build_bundle_contains_zaeon_uri(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert b.get("zaeon_uri", "").startswith("zaeon://")


# ---------------------------------------------------------------------------
# _restore_bundle
# ---------------------------------------------------------------------------


def test_restore_bundle_writes_profile(isolated_aeon_home):
    bundle = {
        "aeon_profile": {"name": "Restored", "archetype": "warrior"},
        "skill_files": {},
        "memory_sql": "",
    }
    restored = _restore_bundle(bundle, force=True)
    assert "aeon_profile.json" in restored
    data = json.loads((isolated_aeon_home / "aeon_profile.json").read_text())
    assert data["name"] == "Restored"


def test_restore_bundle_skips_existing_without_force(isolated_aeon_home):
    (isolated_aeon_home / "aeon_profile.json").write_text('{"name":"Existing"}')
    bundle = {
        "aeon_profile": {"name": "New"},
        "skill_files": {},
        "memory_sql": "",
    }
    restored = _restore_bundle(bundle, force=False)
    assert "aeon_profile.json" not in restored
    assert (
        json.loads((isolated_aeon_home / "aeon_profile.json").read_text())["name"]
        == "Existing"
    )


def test_restore_bundle_writes_skills(isolated_aeon_home):
    bundle = {
        "skills_registry": {"skills": [{"name": "new-skill"}]},
        "skill_files": {"new-skill": "---\nname: new-skill\n---\n"},
        "memory_sql": "",
    }
    restored = _restore_bundle(bundle, force=True)
    assert "skills/new-skill/SKILL.md" in restored
    assert (isolated_aeon_home / "skills" / "new-skill" / "SKILL.md").exists()


def test_restore_bundle_restores_memory(isolated_aeon_home):
    sql = (
        "BEGIN TRANSACTION;\n"
        "CREATE TABLE memories (id INTEGER PRIMARY KEY, content TEXT);\n"
        "INSERT INTO memories VALUES(1,'hello');\n"
        "COMMIT;"
    )
    bundle = {"skill_files": {}, "memory_sql": sql}
    _restore_bundle(bundle, force=True)
    db_path = isolated_aeon_home / "memory_lite.db"
    assert db_path.exists()


def test_restore_bundle_malformed_sql_does_not_raise(isolated_aeon_home):
    """Malformed SQL in memory_sql must not crash — warning is printed but restore continues."""
    bundle = {"skill_files": {}, "memory_sql": "THIS IS NOT VALID SQL;;;"}
    _restore_bundle(bundle, force=True)  # must not raise


# ---------------------------------------------------------------------------
# cmd_id_export / cmd_id_import
# ---------------------------------------------------------------------------


def test_export_creates_encrypted_file(sample_profile, tmp_path, isolated_aeon_home):
    out = tmp_path / "test.zaeon.enc"
    result = cmd_id_export(output=out, passphrase="test-pass")
    assert result == out
    assert out.exists()
    assert out.read_bytes().startswith(_MAGIC)


def test_export_file_size_nonzero(sample_profile, tmp_path, isolated_aeon_home):
    out = tmp_path / "test.zaeon.enc"
    cmd_id_export(output=out, passphrase="pass")
    assert out.stat().st_size > 100


def test_export_empty_passphrase_returns_empty_path(
    sample_profile, tmp_path, isolated_aeon_home, monkeypatch
):
    """When both the supplied passphrase and the prompted passphrase are empty, export aborts."""
    import getpass as _gp

    out = tmp_path / "test.zaeon.enc"
    monkeypatch.setattr(_gp, "getpass", lambda prompt, **kw: "")
    result = cmd_id_export(output=out, passphrase="")
    assert result == Path("") or not out.exists()


def test_export_import_roundtrip(
    sample_profile, sample_skills, tmp_path, isolated_aeon_home
):
    """Export then import restores profile correctly."""
    import shutil

    out = tmp_path / "roundtrip.zaeon.enc"
    cmd_id_export(output=out, passphrase="sovereign")

    # Wipe the aeon home and import
    shutil.rmtree(str(isolated_aeon_home))
    isolated_aeon_home.mkdir()
    cmd_id_import(file=out, passphrase="sovereign", force=True)

    restored_profile = isolated_aeon_home / "aeon_profile.json"
    assert restored_profile.exists()
    data = json.loads(restored_profile.read_text())
    assert data["name"] == "TestAeon"


def test_import_wrong_passphrase_does_not_restore(
    sample_profile, tmp_path, isolated_aeon_home
):
    out = tmp_path / "locked.zaeon.enc"
    cmd_id_export(output=out, passphrase="correct")
    # Try to import with wrong passphrase
    cmd_id_import(file=out, passphrase="wrong", force=True)
    # Profile should NOT have been changed (decrypt fails before restore)
    data = json.loads((isolated_aeon_home / "aeon_profile.json").read_text())
    assert data["name"] == "TestAeon"  # unchanged


def test_import_missing_file_does_not_raise(tmp_path, isolated_aeon_home):
    cmd_id_import(file=tmp_path / "nonexistent.zaeon.enc", passphrase="x", force=True)


def test_import_existing_aeon_without_force_does_not_overwrite(
    sample_profile, tmp_path, isolated_aeon_home
):
    out = tmp_path / "safe.zaeon.enc"
    cmd_id_export(output=out, passphrase="pass")
    # Import without force — should be blocked
    cmd_id_import(file=out, passphrase="pass", force=False)
    # Profile still has original values
    data = json.loads((isolated_aeon_home / "aeon_profile.json").read_text())
    assert data["name"] == "TestAeon"


# ---------------------------------------------------------------------------
# cmd_id_zaeon
# ---------------------------------------------------------------------------


def test_cmd_id_zaeon_no_profile_does_not_raise(isolated_aeon_home):
    cmd_id_zaeon()  # must not raise


def test_cmd_id_zaeon_with_profile_does_not_raise(sample_profile, isolated_aeon_home):
    cmd_id_zaeon()  # must not raise


# ---------------------------------------------------------------------------
# CLI wiring (typer smoke tests)
# ---------------------------------------------------------------------------


def test_cli_id_zaeon_via_typer(sample_profile, isolated_aeon_home):
    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["id", "zaeon"])
    assert result.exit_code == 0


def test_cli_id_export_via_typer(sample_profile, tmp_path, isolated_aeon_home):
    from typer.testing import CliRunner
    from zana.main import app

    out = tmp_path / "cli_test.zaeon.enc"
    runner = CliRunner()
    result = runner.invoke(
        app, ["id", "export", "--output", str(out), "--passphrase", "cli-pass"]
    )
    assert result.exit_code == 0
    assert out.exists()


def test_cli_id_import_missing_file_via_typer(isolated_aeon_home, tmp_path):
    from typer.testing import CliRunner
    from zana.main import app

    missing = tmp_path / "does_not_exist.zaeon.enc"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["id", "import", str(missing), "--passphrase", "x"],
    )
    assert result.exit_code == 0  # graceful — prints error, no exception
