"""
test_wisdom_autoapprove.py — WisdomRule auto-approve, dedup, and stats (S21-D)

Tests for:
  - WisdomQueue.add() — dedup + auto-approve logic
  - WisdomQueue.stats() — absorption analytics
  - cmd_wisdom_propose() — UI output for each return path
  - cmd_wisdom_stats() — analytics display
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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


def _make_rule(
    text: str = "Always validate inputs before processing.",
    confidence: float = 0.75,
    rule_id: str = "test-rule-001",
) -> dict:
    return {
        "id": rule_id,
        "name": text[:60],
        "domain": "general",
        "confidence": confidence,
        "trigger": text,
        "steps": [text],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# WisdomQueue.add() — normal pending path
# ---------------------------------------------------------------------------


def test_add_to_pending_normal_confidence():
    """confidence=0.75 → goes to pending, returns 'pending'."""
    q = WisdomQueue()
    rule = _make_rule(confidence=0.75)
    result = q.add(rule)
    assert result == "pending"
    data = q.load()
    assert len(data["pending"]) == 1
    assert len(data["approved"]) == 0


# ---------------------------------------------------------------------------
# WisdomQueue.add() — auto-approve path
# ---------------------------------------------------------------------------


def test_auto_approve_high_confidence():
    """confidence=0.90 → returns 'auto_approved', rule in approved not pending."""
    q = WisdomQueue()
    rule = _make_rule(confidence=0.90)
    result = q.add(rule)
    assert result == "auto_approved"
    data = q.load()
    assert len(data["approved"]) == 1
    assert len(data["pending"]) == 0


def test_auto_approve_sets_flag():
    """Auto-approved rule has auto_approved=True."""
    q = WisdomQueue()
    rule = _make_rule(confidence=0.95)
    q.add(rule)
    data = q.load()
    assert data["approved"][0].get("auto_approved") is True


def test_auto_approve_threshold_exact_090():
    """Exactly 0.90 triggers auto-approve."""
    q = WisdomQueue()
    rule = _make_rule(confidence=0.90)
    result = q.add(rule)
    assert result == "auto_approved"


def test_auto_approve_below_threshold_089():
    """0.89 does NOT trigger auto-approve — goes to pending."""
    q = WisdomQueue()
    rule = _make_rule(confidence=0.89)
    result = q.add(rule)
    assert result == "pending"


# ---------------------------------------------------------------------------
# WisdomQueue._dedup_check() + add() dedup path
# ---------------------------------------------------------------------------


def test_dedup_blocks_similar_text():
    """Text with ratio>0.85 to existing pending rule → returns 'duplicate', not added."""
    q = WisdomQueue()
    base_text = "Always validate inputs before processing them carefully."
    q.add(_make_rule(text=base_text, confidence=0.75, rule_id="rule-001"))

    # Near-duplicate (same sentence, tiny variation)
    dup_text = "Always validate inputs before processing them carefully!!"
    result = q.add(_make_rule(text=dup_text, confidence=0.75, rule_id="rule-002"))
    assert result == "duplicate"
    data = q.load()
    # Only the original should be in pending
    assert len(data["pending"]) == 1


def test_dedup_allows_different_text():
    """Unrelated text → not duplicate, gets added normally."""
    q = WisdomQueue()
    q.add(_make_rule(text="Always validate inputs.", rule_id="rule-001"))

    different = "Cache database queries for performance improvement."
    result = q.add(_make_rule(text=different, confidence=0.75, rule_id="rule-002"))
    assert result == "pending"
    data = q.load()
    assert len(data["pending"]) == 2


def test_dedup_checks_approved_too():
    """Duplicate of an approved rule is also blocked."""
    q = WisdomQueue()
    # Add with high confidence → goes to approved
    base_text = "Always validate inputs before processing them carefully."
    q.add(_make_rule(text=base_text, confidence=0.92, rule_id="rule-001"))

    dup_text = "Always validate inputs before processing them carefully!!"
    result = q.add(_make_rule(text=dup_text, confidence=0.75, rule_id="rule-002"))
    assert result == "duplicate"


def test_dedup_ratio_boundary_085():
    """Text with ratio exactly at or above 0.85 threshold → blocked (>0.85)."""
    import difflib

    q = WisdomQueue()
    base_text = "A" * 100
    q.add(_make_rule(text=base_text, confidence=0.75, rule_id="rule-base"))

    # Build a text that produces ratio just above 0.85 with base_text
    # Replace last 14 chars — ratio ≈ 86/100 = 0.86
    near_text = "A" * 86 + "B" * 14
    ratio = difflib.SequenceMatcher(None, base_text, near_text).ratio()
    assert ratio > 0.85, f"precondition failed: ratio={ratio}"

    result = q.add(_make_rule(text=near_text, confidence=0.75, rule_id="rule-near"))
    assert result == "duplicate"


# ---------------------------------------------------------------------------
# WisdomQueue.stats()
# ---------------------------------------------------------------------------


def test_stats_empty_queue():
    """Empty queue → all zeros, absorption_rate=0.0."""
    s = WisdomQueue().stats()
    assert s["pending_count"] == 0
    assert s["approved_count"] == 0
    assert s["rejected_count"] == 0
    assert s["total_proposed"] == 0
    assert s["auto_approved_count"] == 0
    assert s["absorption_rate"] == 0.0
    assert s["avg_confidence"] == 0.0


def test_stats_counts_correctly():
    """2 pending, 3 approved → absorption_rate = 3/5 = 0.6."""
    q = WisdomQueue()
    # Inject directly to avoid dedup rejecting similar-text items
    data = q.load()
    data["pending"] = [
        {
            "id": "p0",
            "confidence": 0.75,
            "trigger": "Validate user inputs at all boundaries.",
        },
        {
            "id": "p1",
            "confidence": 0.70,
            "trigger": "Encrypt data at rest using AES-256 standard.",
        },
    ]
    data["approved"] = [
        {
            "id": "a0",
            "confidence": 0.92,
            "trigger": "Cache queries to reduce database load significantly.",
        },
        {
            "id": "a1",
            "confidence": 0.91,
            "trigger": "Use circuit breakers to prevent cascade failures.",
        },
        {
            "id": "a2",
            "confidence": 0.93,
            "trigger": "Monitor latency percentiles not just averages.",
        },
    ]
    q.save(data)

    s = q.stats()
    assert s["pending_count"] == 2
    assert s["approved_count"] == 3
    assert s["total_proposed"] == 5
    assert abs(s["absorption_rate"] - 0.6) < 0.001


def test_stats_auto_approved_count():
    """Counts only rules with auto_approved=True."""
    q = WisdomQueue()
    # Add one regular-approve (manual) and two auto-approved
    data = q.load()
    data["approved"].append(
        {"id": "m1", "name": "manual", "confidence": 0.8}
    )  # no flag
    data["approved"].append(
        {"id": "a1", "name": "auto1", "confidence": 0.92, "auto_approved": True}
    )
    data["approved"].append(
        {"id": "a2", "name": "auto2", "confidence": 0.95, "auto_approved": True}
    )
    q.save(data)

    s = q.stats()
    assert s["auto_approved_count"] == 2
    assert s["approved_count"] == 3


def test_stats_avg_confidence():
    """Average of approved rule confidences computed correctly."""
    q = WisdomQueue()
    data = q.load()
    data["approved"].append({"id": "r1", "confidence": 0.80})
    data["approved"].append({"id": "r2", "confidence": 0.60})
    q.save(data)

    s = q.stats()
    assert abs(s["avg_confidence"] - 0.70) < 0.001


# ---------------------------------------------------------------------------
# cmd_wisdom_propose() — UI output
# ---------------------------------------------------------------------------


def test_cmd_propose_shows_auto_approved_message():
    """High-confidence propose → console prints 'auto-aprobada'."""
    from zana.commands.wisdom import cmd_wisdom_propose

    mock_console = MagicMock()
    with (
        patch("zana.core.wisdom_queue.QUEUE_PATH", wisdom_queue_mod.QUEUE_PATH),
        patch.object(WisdomQueue, "add", return_value="auto_approved"),
    ):
        cmd_wisdom_propose(
            "Siempre valida los inputs antes de procesar.", console=mock_console
        )

    printed = " ".join(str(call) for call in mock_console.print.call_args_list)
    assert "auto-aprobada" in printed


def test_cmd_propose_shows_duplicate_warning():
    """Duplicate propose → warning printed."""
    from zana.commands.wisdom import cmd_wisdom_propose

    mock_console = MagicMock()
    with patch.object(WisdomQueue, "add", return_value="duplicate"):
        cmd_wisdom_propose("Some rule text.", console=mock_console)

    printed = " ".join(str(call) for call in mock_console.print.call_args_list)
    assert "similar" in printed or "85%" in printed


# ---------------------------------------------------------------------------
# cmd_wisdom_stats() — display
# ---------------------------------------------------------------------------


def test_cmd_wisdom_stats_empty():
    """Empty queue → prints 'No hay WisdomRules'."""
    from zana.commands.wisdom import cmd_wisdom_stats

    mock_console = MagicMock()
    cmd_wisdom_stats(console=mock_console)

    printed = " ".join(str(call) for call in mock_console.print.call_args_list)
    assert "No hay WisdomRules" in printed


def test_cmd_wisdom_stats_shows_table():
    """Non-empty queue → table with counts is printed."""
    from zana.commands.wisdom import cmd_wisdom_stats

    q = WisdomQueue()
    q.add(_make_rule(text="Rule one for stats test.", confidence=0.75, rule_id="s1"))
    q.add(
        _make_rule(text="Rule two auto approved here.", confidence=0.95, rule_id="s2")
    )

    mock_console = MagicMock()
    cmd_wisdom_stats(console=mock_console)

    # At minimum the header and the table should have been printed
    assert mock_console.print.call_count >= 2
    printed = " ".join(str(call) for call in mock_console.print.call_args_list)
    assert "WisdomRule Analytics" in printed


def test_cmd_wisdom_stats_high_absorption_message():
    """absorption_rate > 70% → success message printed."""
    from zana.commands.wisdom import cmd_wisdom_stats

    q = WisdomQueue()
    # Inject 4 approved + 1 pending directly to guarantee 80% absorption
    data = q.load()
    data["approved"] = [
        {
            "id": f"ha-{i}",
            "confidence": 0.95,
            "auto_approved": True,
            "trigger": f"Distinct approved rule text number {i}.",
        }
        for i in range(4)
    ]
    data["pending"] = [
        {
            "id": "lo-1",
            "confidence": 0.60,
            "trigger": "Pending low confidence rule separate.",
        }
    ]
    q.save(data)

    mock_console = MagicMock()
    cmd_wisdom_stats(console=mock_console)

    printed = " ".join(str(call) for call in mock_console.print.call_args_list)
    assert "Alta absorción" in printed
