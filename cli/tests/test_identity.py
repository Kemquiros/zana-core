"""
test_identity.py — ZANA ID v1.0: aeon_serializer (AES-256-GCM) + identity commands.

Covers:
  - aeon_serializer: encrypt_bundle / decrypt_bundle / collect_bundle /
    restore_bundle / fingerprint
  - identity.py commands: cmd_id_export, cmd_id_import, cmd_id_fingerprint,
    cmd_id_zaeon

All tests use tmp_path isolation — zero writes to real ~/.zana/.
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from zana.commands.identity import (
    _build_bundle,
    _compute_zaeon_uri,
    _decrypt,
    _derive_key,
    _encrypt,
    _restore_bundle,
    cmd_id_export,
    cmd_id_fingerprint,
    cmd_id_import,
    cmd_id_zaeon,
)
from zana.core.aeon_serializer import (
    _MAGIC,
    _NONCE_LEN,
    _SALT_LEN,
    collect_bundle,
    decrypt_bundle,
    encrypt_bundle,
    fingerprint,
    restore_bundle,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_aeon_home(tmp_path, monkeypatch):
    """Redirect AEON_HOME and derived paths to tmp_path for every test."""
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
    """Write minimal aeon_profile.json + aeon_dna.json."""
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
    """Create a skill entry in the skills directory."""
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


# ===========================================================================
# aeon_serializer — AES-256-GCM tests
# ===========================================================================


# 1. Encrypt → decrypt roundtrip returns identical dict
def test_encrypt_decrypt_roundtrip():
    data = {"key": "value", "numbers": [1, 2, 3], "nested": {"a": True}}
    blob = encrypt_bundle(data, "sovereign-pass")
    result = decrypt_bundle(blob, "sovereign-pass")
    assert result == data


# 2. Wrong passphrase raises ValueError
def test_encrypt_wrong_passphrase_raises():
    blob = encrypt_bundle({"x": 1}, "correct-pass")
    with pytest.raises(ValueError, match="Wrong passphrase"):
        decrypt_bundle(blob, "wrong-pass")


# 3. Two encryptions of the same data produce different blobs (random salt)
def test_encrypt_uses_random_salt():
    data = {"same": "data"}
    blob1 = encrypt_bundle(data, "pass")
    blob2 = encrypt_bundle(data, "pass")
    assert blob1 != blob2


# 4. Two encryptions use different nonces
def test_encrypt_uses_random_nonce():
    data = {"same": "data"}
    blob1 = encrypt_bundle(data, "pass")
    blob2 = encrypt_bundle(data, "pass")
    # Extract nonces (after MAGIC + SALT)
    nonce_offset = len(_MAGIC) + _SALT_LEN
    nonce1 = blob1[nonce_offset : nonce_offset + _NONCE_LEN]
    nonce2 = blob2[nonce_offset : nonce_offset + _NONCE_LEN]
    assert nonce1 != nonce2


# 5. Magic bytes present in every encrypted blob
def test_magic_bytes_present():
    blob = encrypt_bundle({"a": 1}, "pass")
    assert blob[: len(_MAGIC)] == _MAGIC


# 6. collect_bundle gracefully skips missing files
def test_collect_bundle_missing_files(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    bundle = collect_bundle(zana_dir)
    assert bundle["version"] == "1.0"
    assert "exported_at" in bundle
    assert bundle["files"] == {}


# 7. collect_bundle captures all present files
def test_collect_bundle_full(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    profile = {"name": "Tester", "archetype": "mage"}
    dna = {"genes": [1.0] * 5}
    (zana_dir / "aeon_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (zana_dir / "aeon_dna.json").write_text(json.dumps(dna), encoding="utf-8")

    bundle = collect_bundle(zana_dir)

    assert "aeon_profile.json" in bundle["files"]
    assert bundle["files"]["aeon_profile.json"]["name"] == "Tester"
    assert "aeon_dna.json" in bundle["files"]


# 8. restore_bundle writes files to zana_dir
def test_restore_bundle_writes_files(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    bundle = {
        "version": "1.0",
        "files": {
            "aeon_profile.json": {"name": "Restored"},
            "aeon_dna.json": {"genes": [0.1]},
        },
    }
    restored = restore_bundle(bundle, zana_dir, overwrite=True)
    assert "aeon_profile.json" in restored
    assert "aeon_dna.json" in restored
    data = json.loads((zana_dir / "aeon_profile.json").read_text())
    assert data["name"] == "Restored"


# 9. restore_bundle skips existing files when overwrite=False
def test_restore_bundle_skip_existing(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    (zana_dir / "aeon_profile.json").write_text('{"name":"Existing"}', encoding="utf-8")
    bundle = {"files": {"aeon_profile.json": {"name": "New"}}}
    restored = restore_bundle(bundle, zana_dir, overwrite=False)
    assert "aeon_profile.json" not in restored
    existing = json.loads((zana_dir / "aeon_profile.json").read_text())
    assert existing["name"] == "Existing"


# 10. restore_bundle overwrites when overwrite=True
def test_restore_bundle_force_overwrite(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    (zana_dir / "aeon_profile.json").write_text('{"name":"Old"}', encoding="utf-8")
    bundle = {"files": {"aeon_profile.json": {"name": "New"}}}
    restored = restore_bundle(bundle, zana_dir, overwrite=True)
    assert "aeon_profile.json" in restored
    assert json.loads((zana_dir / "aeon_profile.json").read_text())["name"] == "New"


# 11. fingerprint returns exactly 8 chars
def test_fingerprint_8_chars(tmp_path):
    bundle = {"files": {"aeon_dna.json": {"genes": [0.5] * 10}}}
    fp = fingerprint(bundle)
    assert len(fp) == 8


# 12. fingerprint is deterministic for the same input
def test_fingerprint_deterministic():
    bundle = {"files": {"aeon_dna.json": {"genes": [0.1, 0.2, 0.3]}}}
    assert fingerprint(bundle) == fingerprint(bundle)


# 13. cmd_id_export smoke test — creates encrypted file and shows fingerprint
def test_cmd_id_export_smoke(sample_profile, tmp_path, isolated_aeon_home):
    out = tmp_path / "smoke.zaeon.enc"
    result = cmd_id_export(output=out, passphrase="test-pass")
    assert result == out
    assert out.exists()
    # File must start with the legacy Fernet magic (identity.py uses _MAGIC too)
    assert out.read_bytes()[:6] == b"ZAEON\x01"


# 14. cmd_id_import smoke — export then import full roundtrip
def test_cmd_id_import_smoke(
    sample_profile, sample_skills, tmp_path, isolated_aeon_home
):
    import shutil

    out = tmp_path / "roundtrip.zaeon.enc"
    cmd_id_export(output=out, passphrase="sovereign")

    # Wipe aeon home and import
    shutil.rmtree(str(isolated_aeon_home))
    isolated_aeon_home.mkdir()
    cmd_id_import(file=out, passphrase="sovereign", force=True)

    restored_profile = isolated_aeon_home / "aeon_profile.json"
    assert restored_profile.exists()
    data = json.loads(restored_profile.read_text())
    assert data["name"] == "TestAeon"


# 15. cmd_id_import wrong passphrase — clean error, no data written
def test_cmd_id_import_wrong_passphrase(sample_profile, tmp_path, isolated_aeon_home):
    out = tmp_path / "locked.zaeon.enc"
    cmd_id_export(output=out, passphrase="correct")
    cmd_id_import(file=out, passphrase="wrong", force=True)
    # Profile must remain unchanged (decrypt fails before restore)
    data = json.loads((isolated_aeon_home / "aeon_profile.json").read_text())
    assert data["name"] == "TestAeon"


# 16. cmd_id_fingerprint smoke — uses tmp aeon_dna.json, no real ~/.zana writes
def test_cmd_id_fingerprint_smoke(sample_profile, isolated_aeon_home):
    # sample_profile fixture writes aeon_dna.json — fingerprint must not raise
    cmd_id_fingerprint()  # must not raise


# 17. bundle version field is always "1.0"
def test_bundle_version_present(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    bundle = collect_bundle(zana_dir)
    assert bundle["version"] == "1.0"


# 18. bundle exported_at is a valid ISO-8601 string
def test_bundle_exported_at_iso(tmp_path):
    from datetime import datetime

    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    bundle = collect_bundle(zana_dir)
    # Must parse without error
    ts = datetime.fromisoformat(bundle["exported_at"])
    assert ts.tzinfo is not None  # timezone-aware


# 19. Full roundtrip with large bundle (100 wisdom rules)
def test_full_roundtrip_large_bundle(tmp_path):
    zana_dir = tmp_path / "zana_isolated"
    zana_dir.mkdir()
    # Write wisdom_queue with 100 entries
    wisdom = {"queue": [{"rule": f"rule_{i}", "weight": i * 0.01} for i in range(100)]}
    (zana_dir / "wisdom_queue.json").write_text(json.dumps(wisdom), encoding="utf-8")
    (zana_dir / "aeon_profile.json").write_text(
        json.dumps({"name": "LargeAeon"}), encoding="utf-8"
    )

    bundle = collect_bundle(zana_dir)
    blob = encrypt_bundle(bundle, "large-pass")
    recovered = decrypt_bundle(blob, "large-pass")

    # All 100 rules present
    restored_wisdom = recovered["files"]["wisdom_queue.json"]
    assert len(restored_wisdom["queue"]) == 100
    assert restored_wisdom["queue"][99]["rule"] == "rule_99"

    # Verify restore_bundle writes them back
    restore_dir = tmp_path / ".zana_restored"
    restore_dir.mkdir()
    restored_files = restore_bundle(recovered, restore_dir, overwrite=True)
    assert "wisdom_queue.json" in restored_files
    written = json.loads((restore_dir / "wisdom_queue.json").read_text())
    assert len(written["queue"]) == 100


# 20. Tampered ciphertext raises ValueError (GCM tag verification)
def test_decrypt_corrupt_data_raises():
    blob = encrypt_bundle({"secret": "data"}, "passphrase")
    # Flip a byte in the ciphertext (after MAGIC + SALT + NONCE)
    header_len = len(_MAGIC) + _SALT_LEN + _NONCE_LEN
    tampered = bytearray(blob)
    tampered[header_len] ^= 0xFF
    with pytest.raises(ValueError):
        decrypt_bundle(bytes(tampered), "passphrase")


# ===========================================================================
# Legacy identity.py helpers (Fernet-based) — keep existing coverage
# ===========================================================================


def test_derive_key_is_deterministic():
    salt = b"\x00" * 16
    k1 = _derive_key("passphrase", salt)
    k2 = _derive_key("passphrase", salt)
    assert k1 == k2


def test_derive_key_differs_with_different_salt():
    k1 = _derive_key("passphrase", b"\x00" * 16)
    k2 = _derive_key("passphrase", b"\xff" * 16)
    assert k1 != k2


def test_legacy_encrypt_starts_with_magic():
    enc = _encrypt(b"hello", "secret")
    assert enc.startswith(_MAGIC)


def test_legacy_encrypt_decrypt_roundtrip():
    payload = b"sovereign aeon data"
    enc = _encrypt(payload, "my-passphrase")
    dec = _decrypt(enc, "my-passphrase")
    assert dec == payload


def test_legacy_decrypt_wrong_passphrase_raises():
    enc = _encrypt(b"data", "correct")
    with pytest.raises(ValueError, match="Wrong passphrase"):
        _decrypt(enc, "wrong")


def test_zaeon_uri_format(sample_profile, isolated_aeon_home):
    uri = _compute_zaeon_uri()
    assert uri.startswith("zaeon://")
    assert "?id=" in uri


def test_zaeon_uri_is_deterministic(sample_profile, isolated_aeon_home):
    assert _compute_zaeon_uri() == _compute_zaeon_uri()


def test_build_bundle_contains_exported_at(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert "exported_at" in b


def test_build_bundle_contains_profile(sample_profile, isolated_aeon_home):
    b = _build_bundle()
    assert b["aeon_profile"]["name"] == "TestAeon"


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


def test_export_creates_encrypted_file(sample_profile, tmp_path, isolated_aeon_home):
    out = tmp_path / "test.zaeon.enc"
    result = cmd_id_export(output=out, passphrase="test-pass")
    assert result == out
    assert out.exists()
    assert out.read_bytes().startswith(_MAGIC)


def test_import_missing_file_does_not_raise(tmp_path, isolated_aeon_home):
    cmd_id_import(file=tmp_path / "nonexistent.zaeon.enc", passphrase="x", force=True)


def test_cmd_id_zaeon_with_profile_does_not_raise(sample_profile, isolated_aeon_home):
    cmd_id_zaeon()


def test_cli_id_fingerprint_via_typer(sample_profile, isolated_aeon_home):
    from typer.testing import CliRunner
    from zana.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["id", "fingerprint"])
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
