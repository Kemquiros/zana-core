"""Tests for S15-1: shell_guard — sovereign OS execution."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Intent detection ─────────────────────────────────────────────────────────


def test_shell_intent_detected_spanish():
    """'lista mis archivos en Documents' triggers shell intent."""
    from zana.core.zsm import _detect_intent

    intent = _detect_intent("lista mis archivos en ~/Documents")
    assert intent == "shell"


def test_shell_intent_detected_english():
    """'list files in ~/Documents' triggers shell intent."""
    from zana.core.zsm import _detect_intent

    intent = _detect_intent("list files in ~/Documents")
    assert intent == "shell"


# ── Template matching ─────────────────────────────────────────────────────────


def test_template_unknown_shows_help(capsys):
    """Unrecognized query -> help list printed, no subprocess called."""
    console = MagicMock()
    qmod = MagicMock()

    with patch("subprocess.run") as mock_run:
        from zana.core.shell_guard import execute

        execute("haz algo raro con los archivos", console, qmod)
        mock_run.assert_not_called()


def test_template_list_files_builds_correct_argv(tmp_path):
    """'lista mis archivos en <path>' -> argv=['ls', '-la', resolved_path]."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    mock_result = MagicMock()
    mock_result.stdout = "total 0\n"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with (
        patch("subprocess.run", return_value=mock_result) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)

    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    argv = call_kwargs[0][0]
    assert argv[0] == "ls"
    assert argv[1] == "-la"
    assert not call_kwargs.kwargs.get("shell", True)  # shell=False


# ── Parameter validation ──────────────────────────────────────────────────────


def test_path_outside_home_blocked():
    """/etc/passwd as path -> blocked, subprocess not called."""
    console = MagicMock()
    qmod = MagicMock()

    with patch("subprocess.run") as mock_run:
        from zana.core.shell_guard import execute

        execute("lista mis archivos en /etc/passwd", console, qmod)
        mock_run.assert_not_called()


def test_path_sensitive_dir_blocked():
    """~/.ssh as path -> blocked (sensitive directory)."""
    console = MagicMock()
    qmod = MagicMock()

    with patch("subprocess.run") as mock_run:
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {Path.home()}/.ssh", console, qmod)
        mock_run.assert_not_called()


def test_path_zana_dir_blocked():
    """~/.zana as path -> blocked."""
    console = MagicMock()
    qmod = MagicMock()

    with patch("subprocess.run") as mock_run:
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {Path.home()}/.zana", console, qmod)
        mock_run.assert_not_called()


def test_path_symlink_to_etc_blocked(tmp_path):
    """Symlink pointing to /etc -> realpath() detects /etc, blocked."""
    symlink = tmp_path / "evil_link"
    symlink.symlink_to("/etc")

    console = MagicMock()
    qmod = MagicMock()

    with patch("subprocess.run") as mock_run:
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {symlink}", console, qmod)
        mock_run.assert_not_called()


def test_invalid_filename_shell_metacharacters():
    """Filename with ';' -> _validate_filename rejects."""
    from zana.core.shell_guard import _validate_filename

    assert _validate_filename("file; rm -rf ~") is None
    assert _validate_filename("normal_file.txt") is not None


# ── Confirmation gate ─────────────────────────────────────────────────────────


def test_user_cancels_no_subprocess(tmp_path):
    """confirm=False -> no subprocess.run called."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = False  # user says NO

    with patch("subprocess.run") as mock_run, patch("zana.core.shell_guard._audit"):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)
        mock_run.assert_not_called()


def test_user_confirms_subprocess_called(tmp_path):
    """confirm=True -> subprocess.run IS called."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    mock_result = MagicMock(stdout="ok\n", stderr="", returncode=0)

    with (
        patch("subprocess.run", return_value=mock_result) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)
        mock_run.assert_called_once()


# ── Execution security ────────────────────────────────────────────────────────


def test_shell_false_enforced(tmp_path):
    """subprocess.run is always called with shell=False."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    mock_result = MagicMock(stdout="", stderr="", returncode=0)

    with (
        patch("subprocess.run", return_value=mock_result) as mock_run,
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)

    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False


def test_clean_env_no_api_keys_in_subprocess(tmp_path, monkeypatch):
    """subprocess env does NOT contain ANTHROPIC_API_KEY or similar."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-key-12345")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-secret-12345")

    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    captured_env = {}

    def capture_run(argv, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return mock_result

    with (
        patch("subprocess.run", side_effect=capture_run),
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)

    assert "ANTHROPIC_API_KEY" not in captured_env
    assert "GEMINI_API_KEY" not in captured_env


def test_output_ansi_stripped(tmp_path):
    """ANSI escape sequences are removed from output."""
    from zana.core.shell_guard import _strip_ansi

    dirty = "\x1b[32mgreen text\x1b[0m normal"
    clean = _strip_ansi(dirty)
    assert "\x1b" not in clean
    assert "green text" in clean
    assert "normal" in clean


# ── Civic Ledger ──────────────────────────────────────────────────────────────


def test_blocked_path_audited():
    """Blocked path -> audit entry created even without subprocess."""
    console = MagicMock()
    qmod = MagicMock()

    audit_calls = []

    with (
        patch("subprocess.run"),
        patch(
            "zana.core.shell_guard._audit",
            side_effect=lambda *a, **kw: audit_calls.append(a),
        ),
    ):
        from zana.core.shell_guard import execute

        execute("lista mis archivos en /etc/passwd", console, qmod)

    assert len(audit_calls) > 0


def test_cancelled_audited(tmp_path):
    """User cancels -> ShellCancelled audit entry created."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = False

    audit_calls = []

    with (
        patch("subprocess.run"),
        patch(
            "zana.core.shell_guard._audit",
            side_effect=lambda *a, **kw: audit_calls.append(a),
        ),
    ):
        from zana.core.shell_guard import execute

        execute(f"lista mis archivos en {tmp_path}", console, qmod)

    assert any("Cancelled" in str(c) for c in audit_calls)


# ── Timeout ───────────────────────────────────────────────────────────────────


def test_timeout_graceful(tmp_path):
    """TimeoutExpired -> graceful message, no crash."""
    console = MagicMock()
    qmod = MagicMock()
    qmod.confirm.return_value.ask.return_value = True

    with (
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["ls"], 30)),
        patch("zana.core.shell_guard._audit"),
    ):
        from zana.core.shell_guard import execute

        # Should not raise
        execute(f"lista mis archivos en {tmp_path}", console, qmod)
