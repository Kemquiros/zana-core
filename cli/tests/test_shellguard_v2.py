"""Tests for S21-E: ShellGuard v2 — audit UI + 5 new templates."""

from unittest.mock import MagicMock, patch

# ── Helper ────────────────────────────────────────────────────────────────────


def _make_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ══════════════════════════════════════════════════════════════════════════════
# New templates
# ══════════════════════════════════════════════════════════════════════════════


# ── open_file ─────────────────────────────────────────────────────────────────


def test_open_file_trigger_detected(tmp_path):
    """'abre el archivo <path>' → argv[0] == 'xdg-open'."""
    target = tmp_path / "doc.txt"
    target.write_text("hello")

    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch("subprocess.run", return_value=_make_result()) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"abre el archivo {target}", console, qmod)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "xdg-open"
    assert argv[1] == str(target.resolve())
    assert mock_run.call_args.kwargs.get("shell", True) is False


def test_open_file_must_exist(tmp_path):
    """Non-existent file path → subprocess never called."""
    nonexistent = tmp_path / "ghost.txt"
    assert not nonexistent.exists()

    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"abre el archivo {nonexistent}", console, qmod)

    mock_run.assert_not_called()


# ── ping_host ─────────────────────────────────────────────────────────────────


def test_ping_host_trigger_detected():
    """'ping 8.8.8.8' → argv == ['ping', '-c', '3', '8.8.8.8']."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch("subprocess.run", return_value=_make_result("pong")) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("ping 8.8.8.8", console, qmod)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv == ["ping", "-c", "3", "8.8.8.8"]


def test_ping_host_invalid_chars_blocked():
    """'ping 8.8.8.8; rm -rf ~' → blocked, subprocess not called."""
    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("ping 8.8.8.8; rm -rf ~", console, qmod)

    mock_run.assert_not_called()


def test_ping_host_slash_blocked():
    """'ping ../evil' → blocked (slash in hostname)."""
    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("ping ../evil", console, qmod)

    mock_run.assert_not_called()


# ── chmod_safe ────────────────────────────────────────────────────────────────


def test_chmod_safe_allowed_mode_755(tmp_path):
    """mode '755' → argv == ['chmod', '755', '<path>']."""
    target = tmp_path / "script.sh"
    target.write_text("#!/bin/bash")

    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch("subprocess.run", return_value=_make_result()) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"chmod 755 {target}", console, qmod)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "chmod"
    assert argv[1] == "755"
    assert argv[2] == str(target.resolve())


def test_chmod_safe_blocked_mode_777(tmp_path):
    """mode '777' → not in whitelist, subprocess not called."""
    target = tmp_path / "file.sh"
    target.write_text("x")

    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"chmod 777 {target}", console, qmod)

    mock_run.assert_not_called()


def test_chmod_safe_blocked_mode_000(tmp_path):
    """mode '000' → not in whitelist, subprocess not called."""
    target = tmp_path / "file.sh"
    target.write_text("x")

    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"chmod 000 {target}", console, qmod)

    mock_run.assert_not_called()


# ── which_cmd ─────────────────────────────────────────────────────────────────


def test_which_cmd_trigger_detected():
    """'which python3' → argv == ['which', 'python3']."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch(
            "subprocess.run", return_value=_make_result("/usr/bin/python3")
        ) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("which python3", console, qmod)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv == ["which", "python3"]


def test_which_cmd_slash_in_name_blocked():
    """'which /bin/bash' → slash in name → blocked."""
    console = MagicMock()
    qmod = MagicMock()

    with (
        patch("subprocess.run") as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("which /bin/bash", console, qmod)

    mock_run.assert_not_called()


# ── df_disk ───────────────────────────────────────────────────────────────────


def test_df_disk_trigger_detected():
    """'df' → argv == ['df', '-h']."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch(
            "subprocess.run", return_value=_make_result("Filesystem   Size")
        ) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute("df", console, qmod)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv == ["df", "-h"]


# ══════════════════════════════════════════════════════════════════════════════
# shell_audit() function
# ══════════════════════════════════════════════════════════════════════════════


def _make_db_mock(events_by_type: dict):
    """Return a mock SentinelLiteDB that returns fixed event lists by type."""
    db = MagicMock()

    def _events(limit, event_type):
        return events_by_type.get(event_type, [])

    db.events.side_effect = _events
    return db


def test_shell_audit_shows_table():
    """DB with events → table is printed (console.print called)."""
    events = {
        "ShellForbiddenCommand": [{"event_type": "ShellForbiddenCommand"}] * 3,
        "ShellCancelled": [{"event_type": "ShellCancelled"}] * 1,
    }
    db_mock = _make_db_mock(events)

    console = MagicMock()

    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=db_mock):
        from zana.core.shell_guard import shell_audit

        shell_audit(console, top_n=10)

    # console.print must have been called (table + summary)
    assert console.print.called


def test_shell_audit_empty_no_events():
    """Empty DB → 'Sin intentos bloqueados registrados.' message."""
    db_mock = _make_db_mock({})

    console = MagicMock()

    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=db_mock):
        from zana.core.shell_guard import shell_audit

        shell_audit(console, top_n=10)

    # Check that the empty message was printed
    all_calls = " ".join(str(c) for c in console.print.call_args_list)
    assert "Sin intentos" in all_calls


def test_shell_audit_severity_high():
    """ForbiddenCommand → _SEVERITY_MAP maps it to HIGH severity."""
    from zana.core.shell_guard import _SEVERITY_MAP

    label, color = _SEVERITY_MAP["ShellForbiddenCommand"]
    assert label == "HIGH"
    assert color == "red"


def test_shell_audit_severity_medium():
    """ShellCancelled → _SEVERITY_MAP maps it to MEDIUM severity."""
    from zana.core.shell_guard import _SEVERITY_MAP

    label, color = _SEVERITY_MAP["ShellCancelled"]
    assert label == "MEDIUM"
    assert color == "yellow"


def test_shell_audit_db_unavailable():
    """DB raises exception → warning printed, no crash."""
    console = MagicMock()

    with patch(
        "zana.core.sentinel_lite.SentinelLiteDB",
        side_effect=RuntimeError("DB locked"),
    ):
        from zana.core.shell_guard import shell_audit

        # Must not raise
        shell_audit(console, top_n=10)

    assert console.print.called
    all_calls = " ".join(str(c) for c in console.print.call_args_list)
    assert (
        "Cannot read" in all_calls
        or "warning" in all_calls.lower()
        or "DB locked" in all_calls
    )


# ══════════════════════════════════════════════════════════════════════════════
# Validator unit tests
# ══════════════════════════════════════════════════════════════════════════════


def test_validate_hostname_valid():
    """'google.com' → returns 'google.com'."""
    from zana.core.shell_guard import _validate_hostname

    result = _validate_hostname("google.com")
    assert result == "google.com"


def test_validate_hostname_blocks_semicolon():
    """'8.8.8.8;evil' → returns None."""
    from zana.core.shell_guard import _validate_hostname

    assert _validate_hostname("8.8.8.8;evil") is None


def test_validate_hostname_blocks_slash():
    """'host/path' → returns None."""
    from zana.core.shell_guard import _validate_hostname

    assert _validate_hostname("host/path") is None


def test_validate_cmd_name_valid():
    """'python3' → returns 'python3'."""
    from zana.core.shell_guard import _validate_cmd_name

    result = _validate_cmd_name("python3")
    assert result == "python3"


def test_validate_cmd_name_slash_blocked():
    """'/bin/bash' → returns None."""
    from zana.core.shell_guard import _validate_cmd_name

    assert _validate_cmd_name("/bin/bash") is None


def test_validate_chmod_mode_safe():
    """'644' → returns '644'."""
    from zana.core.shell_guard import _validate_chmod_mode

    assert _validate_chmod_mode("644") == "644"


def test_validate_chmod_mode_unsafe():
    """'777' → returns None."""
    from zana.core.shell_guard import _validate_chmod_mode

    assert _validate_chmod_mode("777") is None
