"""Tests for Z-L integration in Z-Sync (S17-A)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# to_zl / from_zl unit tests
# ---------------------------------------------------------------------------


def test_to_zl_encodes_assert_verb():
    from zana.core.wisdom_queue import to_zl

    rule = {"id": "test-rule", "name": "Test", "confidence": 0.9}
    result = to_zl(rule)
    assert "!" in result
    assert "wisdom:rule:test-rule" in result


def test_to_zl_includes_confidence():
    from zana.core.wisdom_queue import to_zl

    rule = {"id": "conf-rule", "confidence": 0.75}
    result = to_zl(rule)
    assert "[conf:0.75]" in result


def test_to_zl_includes_civic_fingerprint():
    from zana.core.wisdom_queue import to_zl

    rule = {"id": "civic-rule", "confidence": 0.8}
    result = to_zl(rule)
    assert "[civic:sha256:" in result


def test_to_zl_includes_delta():
    from zana.core.wisdom_queue import to_zl

    rule = {"id": "delta-rule", "confidence": 0.8}
    result = to_zl(rule)
    assert "[delta:+1]" in result


def test_from_zl_round_trip():
    from zana.core.wisdom_queue import from_zl, to_zl

    rule = {"id": "round-trip", "confidence": 0.85}
    zl_str = to_zl(rule)
    recovered = from_zl(zl_str)
    assert recovered is not None
    assert recovered["id"] == "round-trip"
    assert abs(recovered["confidence"] - 0.85) < 0.01


def test_from_zl_wrong_verb_returns_none():
    from zana.core.wisdom_queue import from_zl

    zl_str = "AEON → wisdom:rule:some-rule [conf:0.80] [delta:+1]"
    assert from_zl(zl_str) is None


def test_from_zl_invalid_target_returns_none():
    from zana.core.wisdom_queue import from_zl

    zl_str = "AEON ! skill:create:some-skill [conf:0.80] [delta:+1]"
    assert from_zl(zl_str) is None


# ---------------------------------------------------------------------------
# _build_feed includes zl_version and zl_message fields
# ---------------------------------------------------------------------------


def test_build_feed_includes_zl_version(tmp_path, monkeypatch):
    from zana.commands import sync as sync_mod

    approved_rule = {
        "id": "feed-rule",
        "name": "Feed Test",
        "confidence": 0.9,
        "civic_hash": "sha256:abc123",
    }

    mock_queue = MagicMock()
    mock_queue.return_value.load.return_value = {
        "pending": [],
        "approved": [approved_rule.copy()],
        "rejected": [],
    }

    with patch("zana.core.wisdom_queue.WisdomQueue", mock_queue):
        feed = sync_mod._build_feed()

    assert feed["zl_version"] == "0.1"
    assert feed["version"] == "1.0"
    assert len(feed["rules"]) == 1
    rule_out = feed["rules"][0]
    assert "zl_message" in rule_out
    assert "!" in rule_out["zl_message"]
