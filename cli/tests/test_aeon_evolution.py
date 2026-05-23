"""Tests for Aeon Mastery Map rank progression (S17-C)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zana.commands.aeon import _get_rank

# ── Rank threshold correctness ────────────────────────────────────────────────


def test_rank_seed_at_zero():
    name, icon, next_t, _ = _get_rank(0)
    assert name == "Seed"
    assert next_t == 1


def test_rank_larva_at_one():
    name, _, next_t, _ = _get_rank(1)
    assert name == "Larva"
    assert next_t == 5


def test_rank_warrior_at_five():
    name, _, next_t, _ = _get_rank(5)
    assert name == "Warrior"
    assert next_t == 15


def test_rank_champion_at_fifteen():
    name, _, next_t, _ = _get_rank(15)
    assert name == "Champion"
    assert next_t == 30


def test_rank_legend_at_thirty():
    name, _, next_t, _ = _get_rank(30)
    assert name == "Legend"
    assert next_t == 50


def test_rank_singularity_at_fifty():
    name, _, next_t, pct = _get_rank(50)
    assert name == "Singularity"
    assert next_t is None
    assert pct == 100


def test_rank_progress_pct_halfway():
    # Warrior starts at 5, Champion at 15 → span 10 → 5 + 5 = 10 → 50%
    _, _, _, pct = _get_rank(10)
    assert pct == 50


# ── cmd_rank display ──────────────────────────────────────────────────────────


def test_cmd_rank_displays_panel():
    """cmd_rank runs without error when WisdomQueue is mocked."""
    mock_queue = MagicMock()
    mock_queue.return_value.stats.return_value = {
        "approved": 5,
        "pending": 0,
        "rejected": 0,
    }

    with patch("zana.core.wisdom_queue.WisdomQueue", mock_queue):
        from zana.commands.aeon import cmd_rank

        cmd_rank()  # Should not raise


# ── cmd_evolve rank-up ────────────────────────────────────────────────────────


def test_cmd_evolve_rank_up_writes_ledger(tmp_path, monkeypatch):
    """When rank advances, cmd_evolve writes new rank to state file."""
    import json

    rank_state = tmp_path / "aeon_rank_state.json"
    rank_state.write_text('{"rank": "Seed", "approved": 0}', encoding="utf-8")

    monkeypatch.setattr("zana.commands.aeon._RANK_STATE_PATH", rank_state)

    mock_queue = MagicMock()
    mock_queue.return_value.stats.return_value = {
        "approved": 5,
        "pending": 0,
        "rejected": 0,
    }
    mock_sentinel = MagicMock()

    with (
        patch("zana.core.wisdom_queue.WisdomQueue", mock_queue),
        patch.dict("sys.modules", {"zana.core.sentinel_lite": mock_sentinel}),
    ):
        from zana.commands.aeon import cmd_evolve

        cmd_evolve()

    saved = json.loads(rank_state.read_text())
    assert saved["rank"] == "Warrior"
    assert saved["approved"] == 5
