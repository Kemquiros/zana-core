"""
test_sentinel_dashboard.py — S21-C

Tests for SentinelLiteDB.threat_summary() and cmd_sentinel_threats().
All tests mock SentinelLiteDB — no real SQLite I/O, no HTTP calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zana.core.sentinel_lite import SentinelLiteDB, get_sentinel_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BLOCKED_TYPES = [
    "ShellForbiddenCommand",
    "ShellInvalidParam",
    "ShellMissingParam",
    "ShellUnknownIntent",
    "ZNetworkPingFailed",
]


def _make_db(tmp_path, monkeypatch) -> SentinelLiteDB:
    """Isolated SentinelLiteDB backed by a temp directory."""
    monkeypatch.setattr(SentinelLiteDB, "DB_PATH", tmp_path / "sentinel_lite.db")
    instance = get_sentinel_db()
    return instance


def _make_summary(
    total: int = 0,
    by_type: dict | None = None,
    blocked_count: int = 0,
    cancelled_count: int = 0,
    executed_count: int = 0,
    block_rate: float = 0.0,
    top_blocked: list | None = None,
    last_event_ts: str | None = None,
) -> dict:
    return {
        "total": total,
        "by_type": by_type or {},
        "blocked_count": blocked_count,
        "cancelled_count": cancelled_count,
        "executed_count": executed_count,
        "block_rate": block_rate,
        "top_blocked": top_blocked or [],
        "last_event_ts": last_event_ts,
    }


# ---------------------------------------------------------------------------
# SentinelLiteDB.threat_summary() unit tests
# ---------------------------------------------------------------------------


def test_threat_summary_empty_db(tmp_path, monkeypatch):
    """Empty DB must return total=0 and block_rate=0.0."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        summary = db.threat_summary()
        assert summary["total"] == 0
        assert summary["block_rate"] == 0.0
        assert summary["blocked_count"] == 0
        assert summary["executed_count"] == 0
        assert summary["cancelled_count"] == 0
        assert summary["top_blocked"] == []
        assert summary["last_event_ts"] is None
    finally:
        db.close()


def test_threat_summary_counts_by_type(tmp_path, monkeypatch):
    """by_type must aggregate counts correctly for each event type."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        db.record("ShellExecuted")
        db.record("ShellExecuted")
        db.record("ShellForbiddenCommand")
        summary = db.threat_summary()
        assert summary["by_type"]["ShellExecuted"] == 2
        assert summary["by_type"]["ShellForbiddenCommand"] == 1
        assert summary["total"] == 3
    finally:
        db.close()


def test_threat_summary_blocked_count(tmp_path, monkeypatch):
    """ShellForbiddenCommand and ShellInvalidParam must be counted as blocked."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        db.record("ShellForbiddenCommand")
        db.record("ShellInvalidParam")
        db.record("ShellExecuted")
        summary = db.threat_summary()
        assert summary["blocked_count"] == 2
        assert summary["executed_count"] == 1
    finally:
        db.close()


def test_threat_summary_block_rate_calculation(tmp_path, monkeypatch):
    """block_rate = blocked / (blocked + executed) = 3 / 10 = 0.30."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        for _ in range(3):
            db.record("ShellForbiddenCommand")
        for _ in range(7):
            db.record("ShellExecuted")
        summary = db.threat_summary()
        assert abs(summary["block_rate"] - 0.30) < 1e-9
    finally:
        db.close()


def test_threat_summary_top_n_respected(tmp_path, monkeypatch):
    """top_n=3 must return at most 3 entries in top_blocked."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        for et in _BLOCKED_TYPES:
            db.record(et)
        summary = db.threat_summary(top_n=3)
        assert len(summary["top_blocked"]) <= 3
    finally:
        db.close()


def test_threat_summary_last_event_ts(tmp_path, monkeypatch):
    """last_event_ts must be the timestamp of the most recent event."""
    db = _make_db(tmp_path, monkeypatch)
    try:
        db.record("ShellExecuted")
        db.record("ShellForbiddenCommand")
        summary = db.threat_summary()
        assert summary["last_event_ts"] is not None
        assert len(summary["last_event_ts"]) > 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# cmd_sentinel_threats() integration tests — mock SentinelLiteDB
# ---------------------------------------------------------------------------


def test_cmd_sentinel_threats_empty(monkeypatch):
    """Empty DB must print the 'No hay eventos' message."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary()

    output_lines: list[str] = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: output_lines.append(
            str(a[0]) if a else ""
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    combined = "\n".join(output_lines)
    assert "No hay eventos" in combined


def test_cmd_sentinel_threats_shows_table(monkeypatch):
    """Non-empty DB must call console.print with a Rich Table object."""
    from rich.table import Table

    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary(
        total=5,
        by_type={"ShellExecuted": 5},
        executed_count=5,
        last_event_ts="2026-05-23 10:00:00",
    )

    printed_objects: list = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: printed_objects.append(
            a[0] if a else None
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    assert any(isinstance(obj, Table) for obj in printed_objects)


def test_cmd_sentinel_threats_high_block_rate_warning(monkeypatch):
    """block_rate > 0.30 must print the ShellGuard warning."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary(
        total=10,
        by_type={"ShellForbiddenCommand": 4, "ShellExecuted": 6},
        blocked_count=4,
        executed_count=6,
        block_rate=0.40,
        last_event_ts="2026-05-23 10:00:00",
    )

    output_lines: list[str] = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: output_lines.append(
            str(a[0]) if a else ""
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    combined = "\n".join(output_lines)
    assert "ShellGuard" in combined
    assert "30%" in combined


def test_cmd_sentinel_threats_normal_block_rate_no_warning(monkeypatch):
    """block_rate <= 0.30 must NOT print the ShellGuard warning."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary(
        total=10,
        by_type={"ShellForbiddenCommand": 2, "ShellExecuted": 8},
        blocked_count=2,
        executed_count=8,
        block_rate=0.20,
        last_event_ts="2026-05-23 10:00:00",
    )

    output_lines: list[str] = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: output_lines.append(
            str(a[0]) if a else ""
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    combined = "\n".join(output_lines)
    assert "ShellGuard" not in combined


def test_cmd_sentinel_threats_bar_chart_rendered(monkeypatch):
    """The bar character (block) must appear in the rendered table."""
    from rich.table import Table

    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary(
        total=5,
        by_type={"ShellExecuted": 5},
        executed_count=5,
        last_event_ts="2026-05-23 10:00:00",
    )

    printed_objects: list = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: printed_objects.append(
            a[0] if a else None
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    tables = [obj for obj in printed_objects if isinstance(obj, Table)]
    assert tables, "Expected at least one Rich Table in output"
    table = tables[0]
    assert table.row_count > 0

    found_bar = False
    for col in table.columns:
        for cell in col._cells:
            if "█" in str(cell):
                found_bar = True
                break
    assert found_bar, "Expected block character (█) in table bar column"


def test_cmd_sentinel_threats_top_n_param(monkeypatch):
    """Custom top_n value must be passed through to threat_summary."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary()

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console"),
    ):
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats(top_n=5)

    mock_db.threat_summary.assert_called_once_with(top_n=5)


def test_cmd_sentinel_threats_header_present(monkeypatch):
    """'Threat Dashboard' must appear in the header output."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary()

    output_lines: list[str] = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: output_lines.append(
            str(a[0]) if a else ""
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    combined = "\n".join(output_lines)
    assert "Threat Dashboard" in combined


def test_cmd_sentinel_threats_summary_row(monkeypatch):
    """Total, blocked, and executed counts must appear in the summary line."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary(
        total=15,
        by_type={"ShellForbiddenCommand": 3, "ShellExecuted": 12},
        blocked_count=3,
        executed_count=12,
        block_rate=0.20,
        last_event_ts="2026-05-23 12:00:00",
    )

    output_lines: list[str] = []

    with (
        patch("zana.commands.sentinel.get_sentinel_db", return_value=mock_db),
        patch("zana.commands.sentinel.console") as mock_console,
    ):
        mock_console.print.side_effect = lambda *a, **kw: output_lines.append(
            str(a[0]) if a else ""
        )
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    combined = "\n".join(output_lines)
    assert "15" in combined
    assert "3" in combined
    assert "12" in combined


def test_cmd_sentinel_threats_civic_ledger_used(monkeypatch):
    """SentinelLiteDB must be instantiated when the command runs."""
    mock_db = MagicMock()
    mock_db.threat_summary.return_value = _make_summary()

    with (
        patch(
            "zana.commands.sentinel.get_sentinel_db", return_value=mock_db
        ) as mock_factory,
        patch("zana.commands.sentinel.console"),
    ):
        from zana.commands.sentinel import cmd_sentinel_threats

        cmd_sentinel_threats()

    mock_factory.assert_called_once()
    mock_db.close.assert_called_once()
