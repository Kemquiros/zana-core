"""Tests for S17-B ShellGuard expansion — 5 new templates + shell history."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_console() -> MagicMock:
    return MagicMock()


def _make_q(answer: bool) -> MagicMock:
    q = MagicMock()
    q.confirm.return_value.ask.return_value = answer
    return q


# ---------------------------------------------------------------------------
# move_file template
# ---------------------------------------------------------------------------


def test_move_file_trigger_detected(tmp_path):
    from zana.core import shell_guard

    src = tmp_path / "source.txt"
    src.write_text("data")
    dst = tmp_path / "dest.txt"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        shell_guard.execute(
            f"mueve el archivo {src} {dst}",
            _make_console(),
            _make_q(True),
        )
    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "mv"
    assert str(src) in argv


def test_move_file_src_must_exist(tmp_path):
    from zana.core import shell_guard

    console = _make_console()
    nonexistent = tmp_path / "ghost.txt"
    dst = tmp_path / "dst.txt"

    with patch("subprocess.run") as mock_run:
        shell_guard.execute(
            f"mueve el archivo {nonexistent} {dst}",
            console,
            _make_q(True),
        )
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# rename_file template
# ---------------------------------------------------------------------------


def test_rename_file_trigger_detected(tmp_path):
    from zana.core import shell_guard

    src = tmp_path / "old.txt"
    src.write_text("x")
    dst = tmp_path / "new.txt"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        shell_guard.execute(
            f"renombra el archivo {src} {dst}",
            _make_console(),
            _make_q(True),
        )
    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "mv"


# ---------------------------------------------------------------------------
# compress_dir template
# ---------------------------------------------------------------------------


def test_compress_dir_trigger_detected(tmp_path):
    from zana.core import shell_guard

    target = tmp_path / "mydir"
    target.mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        shell_guard.execute(
            f"comprime la carpeta {target}",
            _make_console(),
            _make_q(True),
        )
    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "tar"
    assert "czf" in argv
    assert argv[2].endswith(".tar.gz")


def test_compress_dir_src_must_exist(tmp_path):
    from zana.core import shell_guard

    console = _make_console()
    with patch("subprocess.run") as mock_run:
        shell_guard.execute(
            f"comprime la carpeta {tmp_path / 'ghost'}",
            console,
            _make_q(True),
        )
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# git_status template — bypass_denylist
# ---------------------------------------------------------------------------


def test_git_status_bypass_denylist(tmp_path):
    """git is in _FORBIDDEN_COMMANDS but git_status template has bypass_denylist=True."""
    from zana.core import shell_guard

    # tmp_path exists, so path validation passes
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="M file.py", stderr="", returncode=0)
        shell_guard.execute(
            f"git status {tmp_path}",
            _make_console(),
            _make_q(True),
        )
    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "git"
    assert "status" in argv
    assert "--short" in argv


def test_git_status_shell_false_enforced(tmp_path):
    from zana.core import shell_guard

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        shell_guard.execute(
            f"git status {tmp_path}",
            _make_console(),
            _make_q(True),
        )
    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False


# ---------------------------------------------------------------------------
# tail_log template
# ---------------------------------------------------------------------------


def test_tail_log_trigger_detected(tmp_path):
    from zana.core import shell_guard

    logfile = tmp_path / "app.log"
    logfile.write_text("line1\nline2\n")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="line1\nline2", stderr="", returncode=0
        )
        shell_guard.execute(
            f"tail {logfile}",
            _make_console(),
            _make_q(True),
        )
    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "tail"
    assert "-n" in argv
    assert "50" in argv


# ---------------------------------------------------------------------------
# shell_history
# ---------------------------------------------------------------------------


def test_shell_history_shows_entries():
    from zana.core import shell_guard

    fake_rows = [
        {
            "timestamp": "2026-05-23T10:00:00",
            "event_type": "ShellExecuted",
            "civic_hash": "abc123456789xyz",
        },
        {
            "timestamp": "2026-05-23T09:55:00",
            "event_type": "ShellCancelled",
            "civic_hash": "def987654321uvw",
        },
    ]

    mock_db = MagicMock()
    mock_db.events.side_effect = lambda limit, event_type: (
        [r for r in fake_rows if r["event_type"] == event_type]
    )

    console = _make_console()

    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        shell_guard.shell_history(console, limit=20)

    console.print.assert_called()
    all_output = " ".join(str(c) for c in console.print.call_args_list)
    assert "ShellExecuted" in all_output


def test_shell_history_empty_message():
    from zana.core import shell_guard

    mock_db = MagicMock()
    mock_db.events.return_value = []

    console = _make_console()

    with patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db):
        shell_guard.shell_history(console, limit=20)

    all_output = " ".join(str(c) for c in console.print.call_args_list)
    assert "No shell history" in all_output
