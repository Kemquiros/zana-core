"""
Tests for Sprint 18-C: WisdomRule auto-capture from chat + zana wisdom propose.

Coverage:
  - cmd_wisdom_propose() field generation and validation
  - ZSM _detect_intent() for "wisdom_capture" intent
  - Trigger phrase stripping
  - WisdomQueue.add() integration (mocked)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zana.core.zsm import _detect_intent

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_console():
    """Return a mock console that records print calls."""
    return MagicMock()


# ── ZSM intent detection ──────────────────────────────────────────────────────


def test_zsm_detects_recuerda_que():
    assert _detect_intent("recuerda que siempre valida el input") == "wisdom_capture"


def test_zsm_detects_remember_that():
    assert (
        _detect_intent("remember that you should always run tests") == "wisdom_capture"
    )


def test_zsm_detects_rule_colon():
    assert (
        _detect_intent("rule: always validate input before saving") == "wisdom_capture"
    )


def test_zsm_detects_siempre_que():
    assert (
        _detect_intent("siempre que abras un PR, corre los tests") == "wisdom_capture"
    )


def test_zsm_detects_aprende_que():
    assert (
        _detect_intent("aprende que los errores son parte del proceso")
        == "wisdom_capture"
    )


def test_zsm_detects_whenever():
    assert (
        _detect_intent("whenever you deploy, check the health endpoint")
        == "wisdom_capture"
    )


def test_zsm_wisdom_capture_not_caught_as_memory():
    # "recuerda que" should NOT match "memory" intent (which has "recuerda")
    assert _detect_intent("recuerda que debes hacer backups") == "wisdom_capture"


# ── cmd_wisdom_propose — field generation ────────────────────────────────────


def test_propose_creates_pending_entry(tmp_path, monkeypatch):
    """propose() calls WisdomQueue.add() with a proposal dict."""
    monkeypatch.setenv("HOME", str(tmp_path))

    captured = {}

    mock_queue_instance = MagicMock()

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        console = _make_console()
        cmd_wisdom_propose("always validate input before saving to DB", console)

    assert "proposal" in captured
    proposal = captured["proposal"]
    assert "id" in proposal
    assert "name" in proposal
    assert "domain" in proposal
    assert "confidence" in proposal
    assert "trigger" in proposal
    assert "steps" in proposal
    assert "created_at" in proposal


def test_propose_generates_id_from_words(tmp_path, monkeypatch):
    """ID is a slug derived from the first words of the text."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose("always run tests before merge", _make_console())

    rule_id = captured["proposal"]["id"]
    # ID should contain words from the text in slug form
    assert "always" in rule_id or "run" in rule_id or "tests" in rule_id


def test_propose_id_max_40_chars(tmp_path, monkeypatch):
    """Long text must produce an ID truncated to 40 characters."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    long_text = "always validate every single input parameter before saving anything to the database"

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose(long_text, _make_console())

    rule_id = captured["proposal"]["id"]
    assert len(rule_id) <= 40


def test_propose_name_truncated_60_chars(tmp_path, monkeypatch):
    """Name must be truncated to 60 characters."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    long_sentence = "A" * 120  # one very long sentence with no punctuation

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose(long_sentence, _make_console())

    name = captured["proposal"]["name"]
    assert len(name) <= 60


def test_propose_confidence_is_075(tmp_path, monkeypatch):
    """Confidence is always 0.75."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose("run linting before every commit", _make_console())

    assert captured["proposal"]["confidence"] == 0.75


def test_propose_domain_is_general(tmp_path, monkeypatch):
    """Domain is always 'general'."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose("check disk space before large operations", _make_console())

    assert captured["proposal"]["domain"] == "general"


def test_propose_empty_text_no_add(tmp_path, monkeypatch):
    """Empty text must NOT call WisdomQueue.add()."""
    mock_queue_instance = MagicMock()

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        console = _make_console()
        cmd_wisdom_propose("", console)

    mock_queue_instance.add.assert_not_called()


def test_propose_steps_contains_text(tmp_path, monkeypatch):
    """The steps list must contain the original rule text."""
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    rule = "validate schema before inserting records"

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose(rule, _make_console())

    assert rule in captured["proposal"]["steps"]


# ── Trigger stripping ─────────────────────────────────────────────────────────


def test_propose_strips_trigger_phrase(tmp_path, monkeypatch):
    """cmd_wisdom_propose receives text AFTER the trigger phrase is stripped by the ZSM dispatch."""
    # Simulate what the ZSM dispatch does: strip "recuerda que" then pass remainder
    mock_queue_instance = MagicMock()
    captured = {}

    def fake_add(proposal):
        captured["proposal"] = proposal

    mock_queue_instance.add.side_effect = fake_add

    # After stripping "recuerda que " the caller passes the remainder
    stripped_text = "siempre valida el input"

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose(stripped_text, _make_console())

    proposal = captured["proposal"]
    assert proposal["trigger"] == stripped_text
    assert stripped_text in proposal["steps"]


# ── WisdomQueue.add call ──────────────────────────────────────────────────────


def test_propose_calls_queue_add(tmp_path, monkeypatch):
    """WisdomQueue().add() is called exactly once with a dict that has all required keys."""
    mock_queue_instance = MagicMock()

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        cmd_wisdom_propose("always write tests for new features", _make_console())

    mock_queue_instance.add.assert_called_once()
    call_args = mock_queue_instance.add.call_args[0][0]
    required_keys = {
        "id",
        "name",
        "domain",
        "confidence",
        "trigger",
        "steps",
        "created_at",
    }
    assert required_keys.issubset(call_args.keys())


def test_propose_prints_confirmation(tmp_path, monkeypatch):
    """Console receives at least one print call containing 'proposed' or the rule ID."""
    mock_queue_instance = MagicMock()

    with patch("zana.core.wisdom_queue.WisdomQueue", return_value=mock_queue_instance):
        from zana.commands.wisdom import cmd_wisdom_propose

        console = _make_console()
        cmd_wisdom_propose("keep commits small and focused", console)

    assert console.print.call_count >= 1
    all_printed = " ".join(str(c) for c in console.print.call_args_list)
    # Message is now in Spanish: "Regla propuesta" — check for "propuesta" or "proposed" or "wisdomrule"
    assert (
        "propuesta" in all_printed.lower()
        or "proposed" in all_printed.lower()
        or "wisdomrule" in all_printed.lower()
    )
