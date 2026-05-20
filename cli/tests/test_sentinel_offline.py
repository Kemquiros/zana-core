"""
test_sentinel_offline.py — Sprint 9 · P1

Coverage for SentinelLiteDB and offline fallbacks in sentinel commands.
All tests use isolated tmp_path DBs — no real HTTP calls, no Docker required.

Resolves: https://github.com/Kemquiros/zana-core/issues/6
"""

from __future__ import annotations

import pytest

from zana.core.sentinel_lite import SentinelLiteDB, get_sentinel_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Isolated SentinelLiteDB backed by a temp directory."""
    monkeypatch.setattr(SentinelLiteDB, "DB_PATH", tmp_path / "sentinel_lite.db")
    instance = get_sentinel_db()
    yield instance
    instance.close()


# ---------------------------------------------------------------------------
# record()
# ---------------------------------------------------------------------------


def test_record_returns_id(db):
    """record() must return a positive integer row ID."""
    row_id = db.record("PreToolUse")
    assert isinstance(row_id, int)
    assert row_id > 0


def test_record_multiple_events(db):
    """Successive inserts return incrementing IDs."""
    id1 = db.record("PreToolUse")
    id2 = db.record("PostToolUse")
    id3 = db.record("MemoryWrite")
    assert id1 < id2 < id3


# ---------------------------------------------------------------------------
# events()
# ---------------------------------------------------------------------------


def test_events_returns_most_recent_first(db):
    """events() must return rows ordered by id DESC (most recent first)."""
    db.record("PreToolUse")
    db.record("PostToolUse")
    db.record("MemoryWrite")
    evs = db.events(limit=10)
    assert len(evs) == 3
    ids = [e["id"] for e in evs]
    assert ids == sorted(ids, reverse=True), "Events must be most-recent-first"


def test_events_filter_by_event_type(db):
    """events(event_type=...) must only return matching rows."""
    db.record("PreToolUse")
    db.record("MemoryWrite")
    db.record("PreToolUse")
    evs = db.events(limit=10, event_type="PreToolUse")
    assert len(evs) == 2
    assert all(e["event_type"] == "PreToolUse" for e in evs)


def test_events_limit_respected(db):
    """events(limit=N) must return at most N rows."""
    for _ in range(10):
        db.record("PostToolUse")
    evs = db.events(limit=3)
    assert len(evs) == 3


# ---------------------------------------------------------------------------
# ledger()
# ---------------------------------------------------------------------------


def test_ledger_only_returns_entries_with_civic_hash(db):
    """ledger() must exclude events where civic_hash is empty."""
    db.record("PreToolUse", civic_hash="")
    db.record("CivicLedgerEntry", civic_hash="abc123")
    db.record("AeonEvolution", civic_hash="def456")
    entries = db.ledger(limit=10)
    assert len(entries) == 2
    assert all(e["civic_hash"] != "" for e in entries)


def test_ledger_empty_when_no_civic_entries(db):
    """ledger() returns an empty list when no events have a civic_hash."""
    db.record("PreToolUse")
    db.record("PostToolUse")
    entries = db.ledger(limit=10)
    assert entries == []


# ---------------------------------------------------------------------------
# ring buffer pruning
# ---------------------------------------------------------------------------


def test_ring_buffer_prunes_oldest_events(tmp_path, monkeypatch):
    """After MAX_EVENTS + 5 inserts the buffer holds exactly MAX_EVENTS rows."""
    # Use a small MAX_EVENTS value to avoid inserting 1005 rows in tests
    monkeypatch.setattr(SentinelLiteDB, "DB_PATH", tmp_path / "sentinel_lite.db")
    monkeypatch.setattr(SentinelLiteDB, "MAX_EVENTS", 5)

    instance = get_sentinel_db()
    try:
        for i in range(10):  # MAX_EVENTS (5) + 5 extra
            instance.record("PreToolUse")
        evs = instance.events(limit=1000)
        assert len(evs) == 5, f"Expected 5 events after pruning, got {len(evs)}"
    finally:
        instance.close()


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------


def test_stats_total_count(db):
    """stats()['total'] must equal the number of recorded events."""
    assert db.stats()["total"] == 0
    db.record("PreToolUse")
    db.record("PostToolUse")
    assert db.stats()["total"] == 2


def test_stats_by_type_counts(db):
    """stats()['by_type'] must correctly tally each event_type."""
    db.record("PreToolUse")
    db.record("PreToolUse")
    db.record("MemoryWrite")
    stats = db.stats()
    assert stats["by_type"]["PreToolUse"] == 2
    assert stats["by_type"]["MemoryWrite"] == 1


# ---------------------------------------------------------------------------
# Offline command fallbacks — no real HTTP
# ---------------------------------------------------------------------------


def test_cmd_sentinel_events_offline_does_not_raise(tmp_path, monkeypatch):
    """cmd_sentinel_events must not raise when Gateway is unreachable."""
    import httpx

    monkeypatch.setattr(SentinelLiteDB, "DB_PATH", tmp_path / "sentinel_lite.db")

    # Simulate Gateway being offline
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "get", _raise)

    from zana.commands.sentinel import cmd_sentinel_events

    # Must complete without raising
    cmd_sentinel_events(limit=5)


def test_cmd_sentinel_ledger_offline_does_not_raise(tmp_path, monkeypatch):
    """cmd_sentinel_ledger must not raise when Gateway is unreachable."""
    import httpx

    monkeypatch.setattr(SentinelLiteDB, "DB_PATH", tmp_path / "sentinel_lite.db")

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "get", _raise)

    from zana.commands.sentinel import cmd_sentinel_ledger

    # Must complete without raising
    cmd_sentinel_ledger(limit=5)
