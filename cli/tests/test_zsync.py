"""
test_zsync.py — Z-Sync v1.0 tests (Sprint 12, Issue #33)

Covers: civic hash, pull/push/status commands, tamper detection,
        duplicate deduplication, dry-run, peers file persistence.
All tests use tmp_path isolation.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from zana.commands.sync import (
    _civic_hash,
    _load_peers,
    _record_sync,
    _rule_fingerprint,
    _save_peers,
    app,
)

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_aeon_home(tmp_path, monkeypatch):
    aeon_home = tmp_path / ".zana"
    aeon_home.mkdir()
    monkeypatch.setattr("zana.commands.sync._AEON_HOME", aeon_home)
    monkeypatch.setattr(
        "zana.commands.sync._PEERS_FILE", aeon_home / "zsync_peers.json"
    )
    monkeypatch.setattr("zana.commands.sync._FEED_FILE", aeon_home / "zsync_feed.json")
    yield aeon_home


@pytest.fixture
def sample_rule():
    return {
        "id": "rule-001",
        "name": "Greet briefly",
        "domain": "communication",
        "confidence": 0.9,
        "trigger": "greeting",
        "steps": ["say hello"],
        "created_at": "2026-05-01T00:00:00+00:00",
    }


@pytest.fixture
def signed_rule(sample_rule):
    rule = dict(sample_rule)
    rule["civic_hash"] = _rule_fingerprint(rule)
    return rule


@pytest.fixture
def wisdom_queue_mock(tmp_path, monkeypatch):
    """Patch WisdomQueue to use tmp_path storage."""
    queue_path = tmp_path / ".zana" / "wisdom_queue.json"
    monkeypatch.setattr("zana.core.wisdom_queue.QUEUE_PATH", queue_path)
    from zana.core.wisdom_queue import WisdomQueue

    return WisdomQueue()


# ---------------------------------------------------------------------------
# _civic_hash / _rule_fingerprint
# ---------------------------------------------------------------------------


def test_civic_hash_format(sample_rule):
    h = _civic_hash(json.dumps(sample_rule))
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 16


def test_civic_hash_deterministic(sample_rule):
    content = json.dumps(sample_rule)
    assert _civic_hash(content) == _civic_hash(content)


def test_rule_fingerprint_excludes_civic_hash_field(sample_rule):
    rule_with = {**sample_rule, "civic_hash": "sha256:fake1234fake1234"}
    rule_without = dict(sample_rule)
    assert _rule_fingerprint(rule_with) == _rule_fingerprint(rule_without)


def test_rule_fingerprint_differs_on_content_change(sample_rule):
    r1 = dict(sample_rule)
    r2 = {**sample_rule, "name": "Different name"}
    assert _rule_fingerprint(r1) != _rule_fingerprint(r2)


# ---------------------------------------------------------------------------
# Peers store
# ---------------------------------------------------------------------------


def test_load_peers_empty_when_no_file():
    peers = _load_peers()
    assert peers == {}


def test_save_and_load_peers():
    _save_peers({"https://example.com/feed.json": {"last_sync": "2026-05-01"}})
    peers = _load_peers()
    assert "https://example.com/feed.json" in peers


def test_record_sync_creates_entry():
    _record_sync("https://peer.example.com/feed.json", imported=3, total=5)
    peers = _load_peers()
    entry = peers["https://peer.example.com/feed.json"]
    assert entry["imported"] == 3
    assert entry["total"] == 5
    assert "last_sync" in entry


def test_record_sync_overwrites_existing():
    _record_sync("https://peer.example.com/feed.json", imported=1, total=2)
    _record_sync("https://peer.example.com/feed.json", imported=5, total=5)
    peers = _load_peers()
    assert peers["https://peer.example.com/feed.json"]["imported"] == 5


# ---------------------------------------------------------------------------
# zana sync pull
# ---------------------------------------------------------------------------


def _make_feed(rules: list[dict]) -> str:
    return json.dumps(
        {
            "version": "1.0",
            "generated_at": "2026-05-20T00:00:00+00:00",
            "count": len(rules),
            "rules": rules,
        }
    )


def test_sync_pull_imports_valid_rule(signed_rule, wisdom_queue_mock):
    feed_json = _make_feed([signed_rule])
    mock_resp = MagicMock()
    mock_resp.read.return_value = feed_json.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(app, ["pull", "https://example.com/feed.json"])

    assert result.exit_code == 0
    assert "Imported 1" in result.output


def test_sync_pull_rejects_tampered_rule(sample_rule, wisdom_queue_mock):
    tampered = {**sample_rule, "civic_hash": "sha256:aaaaaaaaaaaaaaaa"}
    feed_json = _make_feed([tampered])
    mock_resp = MagicMock()
    mock_resp.read.return_value = feed_json.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(app, ["pull", "https://example.com/feed.json"])

    assert result.exit_code == 0
    assert "tampered" in result.output
    assert "Imported 0" in result.output


def test_sync_pull_deduplicates_existing_rule(signed_rule, wisdom_queue_mock):
    wisdom_queue_mock.add({**signed_rule, "approved_at": "2026-05-01"})
    data = wisdom_queue_mock.load()
    data["approved"] = data.pop("pending", [])
    wisdom_queue_mock.save(data)

    feed_json = _make_feed([signed_rule])
    mock_resp = MagicMock()
    mock_resp.read.return_value = feed_json.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(app, ["pull", "https://example.com/feed.json"])

    assert result.exit_code == 0
    assert "Imported 0" in result.output


def test_sync_pull_network_error_exits_nonzero():
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = runner.invoke(
            app, ["pull", "https://unreachable.example.com/feed.json"]
        )
    assert result.exit_code != 0


def test_sync_pull_invalid_json_exits_nonzero():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"NOT JSON"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(app, ["pull", "https://example.com/feed.json"])
    assert result.exit_code != 0


def test_sync_pull_dry_run_does_not_import(signed_rule, wisdom_queue_mock):
    feed_json = _make_feed([signed_rule])
    mock_resp = MagicMock()
    mock_resp.read.return_value = feed_json.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(
            app, ["pull", "--dry-run", "https://example.com/feed.json"]
        )

    assert result.exit_code == 0
    assert "Dry-run" in result.output
    assert wisdom_queue_mock.stats()["pending"] == 0


def test_sync_pull_records_peer_after_success(signed_rule, wisdom_queue_mock):
    feed_json = _make_feed([signed_rule])
    mock_resp = MagicMock()
    mock_resp.read.return_value = feed_json.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        runner.invoke(app, ["pull", "https://mypeer.com/feed.json"])

    peers = _load_peers()
    assert "https://mypeer.com/feed.json" in peers


# ---------------------------------------------------------------------------
# zana sync push
# ---------------------------------------------------------------------------


def test_sync_push_creates_feed_file(wisdom_queue_mock, isolated_aeon_home):
    result = runner.invoke(app, ["push"])
    assert result.exit_code == 0
    feed_path = isolated_aeon_home / "zsync_feed.json"
    assert feed_path.exists()


def test_sync_push_feed_has_required_fields(wisdom_queue_mock, isolated_aeon_home):
    runner.invoke(app, ["push"])
    feed = json.loads((isolated_aeon_home / "zsync_feed.json").read_text())
    assert "version" in feed
    assert "generated_at" in feed
    assert "rules" in feed
    assert "count" in feed


def test_sync_push_custom_output(wisdom_queue_mock, tmp_path):
    out = tmp_path / "my_feed.json"
    result = runner.invoke(app, ["push", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_sync_push_adds_civic_hash_to_rules(wisdom_queue_mock, isolated_aeon_home):
    wisdom_queue_mock.add(
        {
            "id": "rule-999",
            "name": "Test rule",
            "domain": "test",
            "confidence": 0.8,
            "trigger": "test",
            "steps": ["step1"],
            "created_at": "2026-05-01",
            "approved_at": "2026-05-02",
        }
    )
    data = wisdom_queue_mock.load()
    data["approved"] = data.pop("pending", [])
    wisdom_queue_mock.save(data)

    runner.invoke(app, ["push"])
    feed = json.loads((isolated_aeon_home / "zsync_feed.json").read_text())
    for rule in feed.get("rules", []):
        assert "civic_hash" in rule
        assert rule["civic_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# zana sync status
# ---------------------------------------------------------------------------


def test_sync_status_empty():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No peers" in result.output


def test_sync_status_shows_peer():
    _record_sync("https://alice.example.com/feed.json", imported=7, total=10)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "alice.example.com" in result.output
    assert "7 / 10" in result.output


def test_sync_status_multiple_peers():
    _record_sync("https://alice.example.com/feed.json", imported=2, total=3)
    _record_sync("https://bob.example.com/feed.json", imported=5, total=5)
    result = runner.invoke(app, ["status"])
    assert "alice.example.com" in result.output
    assert "bob.example.com" in result.output


# ---------------------------------------------------------------------------
# zana sync init (legacy — must not crash)
# ---------------------------------------------------------------------------


def test_sync_init_does_not_raise():
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
