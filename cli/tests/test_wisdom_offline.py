"""
test_wisdom_offline.py — Wisdom offline fallback tests (Sprint 9 · Issue #5)

Tests for WisdomQueue class and offline fallback paths in wisdom commands.
No real HTTP calls — Gateway is mocked as unreachable via monkeypatch.
All tests use tmp_path isolation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import zana.core.wisdom_queue as wisdom_queue_mod
from zana.core.wisdom_queue import WisdomQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_queue(tmp_path, monkeypatch):
    """Redirect QUEUE_PATH to a temp directory for every test."""
    queue_path = tmp_path / "wisdom_queue.json"
    monkeypatch.setattr(wisdom_queue_mod, "QUEUE_PATH", queue_path)
    yield queue_path


# ---------------------------------------------------------------------------
# WisdomQueue.load / save
# ---------------------------------------------------------------------------


def test_load_creates_default_when_file_missing(isolated_queue):
    q = WisdomQueue()
    data = q.load()
    assert "pending" in data
    assert "approved" in data
    assert "rejected" in data
    assert data["pending"] == []


def test_load_creates_file_on_disk(isolated_queue):
    WisdomQueue().load()
    assert isolated_queue.exists()


def test_save_and_load_roundtrip(isolated_queue):
    q = WisdomQueue()
    q.save(
        {
            "pending": [{"id": "abc", "name": "TestSkill"}],
            "approved": [],
            "rejected": [],
        }
    )
    loaded = q.load()
    assert loaded["pending"][0]["id"] == "abc"


def test_load_returns_empty_on_corrupt_json(isolated_queue):
    isolated_queue.write_text("{ not valid json }")
    data = WisdomQueue().load()
    assert data == {"pending": [], "approved": [], "rejected": []}


def test_atomic_write_leaves_no_tmp_file(isolated_queue):
    WisdomQueue().save({"pending": [], "approved": [], "rejected": []})
    tmp = isolated_queue.with_suffix(".tmp")
    assert not tmp.exists()


# ---------------------------------------------------------------------------
# WisdomQueue.inbox / stats / add
# ---------------------------------------------------------------------------


def test_inbox_returns_pending_list(isolated_queue):
    q = WisdomQueue()
    q.save(
        {"pending": [{"id": "p1", "name": "Skill1"}], "approved": [], "rejected": []}
    )
    assert len(q.inbox()) == 1
    assert q.inbox()[0]["id"] == "p1"


def test_stats_counts_all_statuses(isolated_queue):
    q = WisdomQueue()
    q.save(
        {
            "pending": [{"id": "p1"}],
            "approved": [{"id": "a1"}, {"id": "a2"}],
            "rejected": [],
        }
    )
    stats = q.stats()
    assert stats["pending"] == 1
    assert stats["approved"] == 2
    assert stats["rejected"] == 0


def test_add_appends_to_pending(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "new-1", "name": "NewSkill", "confidence": 0.9})
    assert len(q.inbox()) == 1
    assert q.inbox()[0]["name"] == "NewSkill"


# ---------------------------------------------------------------------------
# WisdomQueue.approve
# ---------------------------------------------------------------------------


def test_approve_existing_id_returns_item(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "skill-1", "name": "SkillOne"})
    result = q.approve("skill-1")
    assert result is not None
    assert result["id"] == "skill-1"


def test_approve_nonexistent_id_returns_none(isolated_queue):
    q = WisdomQueue()
    assert q.approve("ghost-id") is None


def test_approve_moves_item_to_approved_list(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "moveme", "name": "MoveSkill"})
    q.approve("moveme")
    data = q.load()
    assert len(data["pending"]) == 0
    assert any(s["id"] == "moveme" for s in data["approved"])


def test_approve_sets_approved_at_timestamp(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "ts-skill", "name": "TimestampSkill"})
    item = q.approve("ts-skill")
    assert "approved_at" in item


# ---------------------------------------------------------------------------
# WisdomQueue.reject
# ---------------------------------------------------------------------------


def test_reject_existing_id_returns_true(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "reject-me", "name": "ToReject"})
    assert q.reject("reject-me") is True


def test_reject_nonexistent_id_returns_false(isolated_queue):
    assert WisdomQueue().reject("ghost-id") is False


def test_reject_moves_item_to_rejected_list(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "trash", "name": "TrashSkill"})
    q.reject("trash")
    data = q.load()
    assert len(data["pending"]) == 0
    assert any(s["id"] == "trash" for s in data["rejected"])


# ---------------------------------------------------------------------------
# Offline command fallbacks (Gateway mocked as unreachable)
# ---------------------------------------------------------------------------


def test_cmd_wisdom_inbox_offline_does_not_raise(isolated_queue):
    with patch("zana.commands.wisdom._is_gateway_online", return_value=False):
        from zana.commands.wisdom import cmd_wisdom_inbox

        cmd_wisdom_inbox()  # must not raise


def test_cmd_wisdom_mine_offline_does_not_raise(isolated_queue):
    with patch("zana.commands.wisdom._is_gateway_online", return_value=False):
        from zana.commands.wisdom import cmd_wisdom_mine

        cmd_wisdom_mine()  # must not raise


def test_cmd_wisdom_approve_offline_found(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "approve-offline", "name": "OfflineSkill"})
    with patch("zana.commands.wisdom._is_gateway_online", return_value=False):
        from zana.commands.wisdom import cmd_wisdom_approve

        cmd_wisdom_approve("approve-offline")  # must not raise
    assert q.load()["approved"][0]["id"] == "approve-offline"


def test_cmd_wisdom_reject_offline_found(isolated_queue):
    q = WisdomQueue()
    q.add({"id": "reject-offline", "name": "OfflineSkill"})
    with patch("zana.commands.wisdom._is_gateway_online", return_value=False):
        from zana.commands.wisdom import cmd_wisdom_reject

        cmd_wisdom_reject("reject-offline")  # must not raise
    assert q.load()["rejected"][0]["id"] == "reject-offline"
