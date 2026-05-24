"""Smoke tests — every major command must not crash and must produce output."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _console() -> MagicMock:
    return MagicMock()


def _q(answer: bool = False) -> MagicMock:
    q = MagicMock()
    q.confirm.return_value.ask.return_value = answer
    return q


# ── Memory ─────────────────────────────────────────────────────────────────


def test_smoke_memory_add(tmp_path):
    from zana.commands.memory import cmd_memory_add

    with patch("zana.commands.memory._DB_PATH", tmp_path / "mem.db"):
        cmd_memory_add("smoke test fact", source="smoke", tag="test")


def test_smoke_memory_search(tmp_path):
    from zana.commands.memory import cmd_memory_search

    with patch("zana.commands.memory._DB_PATH", tmp_path / "mem.db"):
        cmd_memory_search("smoke")


def test_smoke_memory_stats(tmp_path):
    from zana.commands.memory import cmd_memory_stats

    with patch("zana.commands.memory._DB_PATH", tmp_path / "mem.db"):
        cmd_memory_stats()


def test_smoke_memory_reflect():
    from zana.commands.memory import cmd_memory_reflect

    mock_add = MagicMock()
    with patch("zana.commands.memory.cmd_memory_add", mock_add):
        cmd_memory_reflect("My name is John. I work at VECANOVA. I live in Medellín.")
    assert mock_add.call_count >= 1


def test_smoke_memory_clear_cancelled(tmp_path):
    from zana.commands.memory import cmd_memory_clear

    with patch("zana.core.memory_lite.MemoryLiteDB.DB_PATH", tmp_path / "mem.db"):
        cmd_memory_clear()


# ── Wisdom ─────────────────────────────────────────────────────────────────


def test_smoke_wisdom_propose_pending(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose

    queue_path = tmp_path / "wisdom_queue.json"
    with patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path):
        cmd_wisdom_propose("Always write tests before shipping code", confidence=0.5)


def test_smoke_wisdom_propose_auto_approve(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose

    queue_path = tmp_path / "wisdom_queue.json"
    mock_db = MagicMock()
    with (
        patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path),
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
    ):
        cmd_wisdom_propose(
            "All critical bugs must be hotfixed immediately", confidence=0.95
        )


def test_smoke_wisdom_propose_duplicate(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose

    queue_path = tmp_path / "wisdom_queue.json"
    with patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path):
        cmd_wisdom_propose("Write tests for every feature", confidence=0.5)
        cmd_wisdom_propose("Write tests for every feature", confidence=0.5)


def test_smoke_wisdom_inbox_empty(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_inbox

    queue_path = tmp_path / "wisdom_queue.json"
    with patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path):
        cmd_wisdom_inbox()


def test_smoke_wisdom_stats_empty(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_stats

    queue_path = tmp_path / "wisdom_queue.json"
    console = _console()
    with patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path):
        cmd_wisdom_stats(console=console)
    output = " ".join(str(c) for c in console.print.call_args_list)
    assert "WisdomRule" in output or "wisdom" in output.lower() or "No hay" in output


def test_smoke_wisdom_stats_with_data(tmp_path):
    from zana.commands.wisdom import cmd_wisdom_propose, cmd_wisdom_stats

    queue_path = tmp_path / "wisdom_queue.json"
    console = _console()
    with patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path):
        cmd_wisdom_propose("Test rule alpha", confidence=0.95)
        cmd_wisdom_propose("Test rule beta", confidence=0.5)
        cmd_wisdom_stats(console=console)
    assert console.print.call_count >= 1


# ── Sentinel ───────────────────────────────────────────────────────────────


def test_smoke_sentinel_events():
    mock_db = MagicMock()
    mock_db.events.return_value = []
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        from zana.commands.sentinel import cmd_sentinel_events

        cmd_sentinel_events(limit=5)


def test_smoke_sentinel_status():
    mock_db = MagicMock()
    mock_db.events.return_value = []
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        from zana.commands.sentinel import cmd_sentinel_status

        cmd_sentinel_status()


def test_smoke_sentinel_threats_empty():
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = {
        "total": 0,
        "by_type": {},
        "blocked_count": 0,
        "cancelled_count": 0,
        "executed_count": 0,
        "block_rate": 0.0,
        "top_blocked": [],
        "last_event_ts": None,
    }
    console = _console()
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        from zana.commands.sentinel import cmd_sentinel_threats

        with patch("zana.commands.sentinel.console", console):
            cmd_sentinel_threats(top_n=10)
    assert console.print.call_count >= 1


def test_smoke_sentinel_threats_with_data():
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = {
        "total": 20,
        "by_type": {
            "ShellExecuted": 15,
            "ShellForbiddenCommand": 3,
            "ShellCancelled": 2,
        },
        "blocked_count": 3,
        "cancelled_count": 2,
        "executed_count": 15,
        "block_rate": 0.17,
        "top_blocked": [("ShellForbiddenCommand", 3)],
        "last_event_ts": "2026-05-23T20:00:00",
    }
    console = _console()
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        from zana.commands.sentinel import cmd_sentinel_threats

        with patch("zana.commands.sentinel.console", console):
            cmd_sentinel_threats(top_n=10)
    output = " ".join(str(c) for c in console.print.call_args_list)
    assert "ShellExecuted" in output or "20" in output or "block" in output.lower()


# ── Skill ──────────────────────────────────────────────────────────────────


def test_smoke_skill_list_empty(tmp_path):
    registry = tmp_path / "registry.json"
    with patch("zana.commands.skill._REGISTRY_PATH", registry):
        from zana.commands.skill import cmd_skill_list

        cmd_skill_list()


def test_smoke_skill_search_local_no_results(tmp_path):
    registry = tmp_path / "registry.json"
    with patch("zana.commands.skill._REGISTRY_PATH", registry):
        from zana.commands.skill import _cmd_skill_search_local

        _cmd_skill_search_local("nonexistentskillxyz")


def test_smoke_skill_create(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    registry = tmp_path / "registry.json"
    with (
        patch("zana.commands.skill.SKILLS_DIR", skills_dir),
        patch("zana.commands.skill.REGISTRY_PATH", registry),
    ):
        from zana.commands.skill import cmd_skill_create

        cmd_skill_create("smoke-skill", description="A smoke test skill", domain="test")
    assert (skills_dir / "smoke-skill" / "SKILL.md").exists()


# ── Aeon ───────────────────────────────────────────────────────────────────


def test_smoke_aeon_status():
    from zana.commands.aeon import cmd_status

    with patch.dict("os.environ", {}, clear=False):
        cmd_status()


def test_smoke_aeon_rank(tmp_path):
    queue_path = tmp_path / "wisdom_queue.json"
    rank_path = tmp_path / "rank.json"
    with (
        patch("zana.core.wisdom_queue.QUEUE_PATH", queue_path),
        patch("zana.commands.aeon._RANK_STATE_PATH", rank_path),
    ):
        from zana.commands.aeon import cmd_rank

        cmd_rank()


def test_smoke_aeon_peers_empty(tmp_path):
    peers_path = tmp_path / "aeon_peers.json"
    with patch("zana.commands.aeon._PEERS_PATH", peers_path):
        from zana.commands.aeon import cmd_aeon_peers

        cmd_aeon_peers()


def test_smoke_aeon_connect_invalid_url(tmp_path):
    peers_path = tmp_path / "aeon_peers.json"
    console = _console()
    with patch("zana.commands.aeon._PEERS_PATH", peers_path):
        from zana.commands.aeon import cmd_aeon_connect

        with patch("zana.commands.aeon.console", console):
            cmd_aeon_connect("http://not-https.com")
    assert not peers_path.exists()


def test_smoke_aeon_ping_not_registered(tmp_path):
    peers_path = tmp_path / "aeon_peers.json"
    console = _console()
    with patch("zana.commands.aeon._PEERS_PATH", peers_path):
        from zana.commands.aeon import cmd_aeon_ping

        with patch("zana.commands.aeon.console", console):
            cmd_aeon_ping("https://unknown-peer.example.com")
    output = " ".join(str(c) for c in console.print.call_args_list)
    assert (
        "no" in output.lower()
        or "registrado" in output.lower()
        or "warning" in output.lower()
    )


def test_smoke_aeon_disconnect_not_found(tmp_path):
    peers_path = tmp_path / "aeon_peers.json"
    console = _console()
    with patch("zana.commands.aeon._PEERS_PATH", peers_path):
        from zana.commands.aeon import cmd_aeon_disconnect

        with patch("zana.commands.aeon.console", console):
            cmd_aeon_disconnect("https://ghost-peer.example.com")
    assert console.print.call_count >= 1


# ── Shell ──────────────────────────────────────────────────────────────────


def test_smoke_shell_unknown_intent():
    from zana.core import shell_guard

    console = _console()
    with patch("subprocess.run") as mock_run:
        shell_guard.execute("xyzzy frobnicator unknown", console, _q(False))
    mock_run.assert_not_called()
    assert console.print.call_count >= 1


def test_smoke_shell_history():
    from zana.core import shell_guard

    mock_db = MagicMock()
    mock_db.events.return_value = []
    console = _console()
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        shell_guard.shell_history(console, limit=5)
    assert console.print.call_count >= 1


def test_smoke_shell_audit_empty():
    from zana.core import shell_guard

    mock_db = MagicMock()
    mock_db.events.return_value = []
    console = _console()
    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        shell_guard.shell_audit(console)
    assert console.print.call_count >= 1


# ── Herald ─────────────────────────────────────────────────────────────────


def test_smoke_herald_slack_invalid_url():
    from zana.commands.herald import cmd_herald_notify_slack

    console = _console()
    with patch("urllib.request.urlopen") as mock_urlopen:
        with patch("zana.commands.herald.console", console):
            try:
                cmd_herald_notify_slack("http://not-https.slack.com/webhook", "test")
            except (SystemExit, Exception):
                pass
    mock_urlopen.assert_not_called()


def test_smoke_herald_email_no_smtp_host():
    import os

    from zana.commands.herald import cmd_herald_notify_email

    console = _console()
    env = {k: v for k, v in os.environ.items() if not k.startswith("ZANA_SMTP")}
    with patch.dict("os.environ", env, clear=True):
        with patch("smtplib.SMTP") as mock_smtp:
            with patch("zana.commands.herald.console", console):
                try:
                    cmd_herald_notify_email("user@example.com", "test message")
                except (SystemExit, Exception):
                    pass
    mock_smtp.assert_not_called()


# ── ZSM dispatch ───────────────────────────────────────────────────────────


def test_smoke_zsm_unknown_query():
    from zana.core.zsm import respond

    # respond() takes only query — uses its own console
    with patch("zana.core.zsm.console") as mock_console:
        respond("xyzzy frobnicator completely unknown gibberish 12345")
    assert mock_console.print.call_count >= 1


def test_smoke_zsm_shell_dispatches():
    from zana.core.zsm import respond

    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        with patch("zana.core.sentinel_lite.SentinelLiteDB"):
            with patch("questionary.confirm") as mock_confirm:
                mock_confirm.return_value.ask.return_value = False
                with patch("zana.core.zsm.console"):
                    respond("lista mis archivos en /tmp")
