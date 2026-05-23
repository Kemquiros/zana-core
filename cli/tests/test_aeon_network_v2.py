"""Tests for Z-Network v0.2 — ping + disconnect (S20-D)."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PEER_URL = "https://peer.example.com"
_PEER_URL_2 = "https://node.example.com"


def _make_peers(url: str = _PEER_URL) -> dict:
    return {
        url: {
            "name": "test-peer",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }


def _setup_peers(tmp_path: Path, monkeypatch, peers: dict) -> Path:
    """Write a peers file and monkeypatch _PEERS_PATH in the aeon module."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    peers_file.write_text(json.dumps(peers, indent=2), encoding="utf-8")
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)
    return peers_file


def _mock_urlopen_ok():
    """Return a context-manager mock that simulates HTTP 200."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    return mock_resp


# ---------------------------------------------------------------------------
# cmd_aeon_ping — success path
# ---------------------------------------------------------------------------


def test_ping_success(tmp_path, monkeypatch):
    """Successful ping updates last_seen in the peers file."""
    import zana.commands.aeon as aeon_mod

    peers_file = _setup_peers(tmp_path, monkeypatch, _make_peers())

    mock_resp = _mock_urlopen_ok()
    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert data[_PEER_URL]["last_seen"] is not None


def test_ping_peer_not_registered(tmp_path, monkeypatch):
    """Ping for an unknown peer prints a warning and never calls urlopen."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    printed = []
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_ping("https://unknown.example.com")

        mock_urlopen.assert_not_called()

    output = " ".join(printed)
    assert "no registrado" in output.lower() or "warning" in output.lower()


def test_ping_invalid_url(tmp_path, monkeypatch):
    """Ping with a non-https URL prints an error and never calls urlopen."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    printed = []
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_ping("http://insecure.example.com")

        mock_urlopen.assert_not_called()

    output = " ".join(printed)
    assert "error" in output.lower() or "https" in output.lower()


def test_ping_url_error(tmp_path, monkeypatch):
    """URLError during ping prints a failure message."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    printed = []
    with (
        patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    output = " ".join(printed)
    assert "no responde" in output or "error" in output.lower()


def test_ping_timeout(tmp_path, monkeypatch):
    """socket.timeout during ping prints a failure message."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    printed = []
    with (
        patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    output = " ".join(printed)
    assert "no responde" in output or "error" in output.lower()


# ---------------------------------------------------------------------------
# cmd_aeon_ping — Civic Ledger
# ---------------------------------------------------------------------------


def test_ping_civic_ledger_success(tmp_path, monkeypatch):
    """On success, SentinelLiteDB.record is called with 'ZNetworkPing'."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    mock_resp = _mock_urlopen_ok()
    mock_db = MagicMock()

    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    mock_db.record.assert_called_once()
    event_type = mock_db.record.call_args[0][0]
    assert event_type == "ZNetworkPing"


def test_ping_civic_ledger_fail(tmp_path, monkeypatch):
    """On URLError, SentinelLiteDB.record is called with 'ZNetworkPingFailed'."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    mock_db = MagicMock()

    with (
        patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("refused"),
        ),
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    mock_db.record.assert_called_once()
    event_type = mock_db.record.call_args[0][0]
    assert event_type == "ZNetworkPingFailed"


# ---------------------------------------------------------------------------
# cmd_aeon_ping — latency measurement
# ---------------------------------------------------------------------------


def test_ping_latency_measured(tmp_path, monkeypatch):
    """Elapsed ms must appear in the success console.print output."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    mock_resp = _mock_urlopen_ok()
    printed = []

    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_ping(_PEER_URL)

    output = " ".join(printed)
    # The success message contains "ms" from the latency display
    assert "ms" in output


# ---------------------------------------------------------------------------
# cmd_aeon_disconnect — success path
# ---------------------------------------------------------------------------


def test_disconnect_success(tmp_path, monkeypatch):
    """Disconnect removes the peer and writes the updated file."""
    import zana.commands.aeon as aeon_mod

    peers = _make_peers()
    peers["https://other.example.com"] = {
        "name": "other",
        "connected_at": "2026-05-01T00:00:00+00:00",
        "last_seen": None,
    }
    peers_file = _setup_peers(tmp_path, monkeypatch, peers)

    printed = []
    with patch.object(aeon_mod.console, "print") as mock_print:
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_disconnect(_PEER_URL)

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert _PEER_URL not in data
    assert "https://other.example.com" in data  # other peer untouched

    output = " ".join(printed)
    assert "desconectado" in output.lower() or "success" in output.lower()


def test_disconnect_peer_not_found(tmp_path, monkeypatch):
    """Disconnect for unknown peer prints warning, does NOT rewrite file."""
    import zana.commands.aeon as aeon_mod

    peers_file = _setup_peers(tmp_path, monkeypatch, _make_peers())
    original_mtime = peers_file.stat().st_mtime

    printed = []
    with patch.object(aeon_mod.console, "print") as mock_print:
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_disconnect("https://ghost.example.com")

    # File should not have been rewritten
    assert peers_file.stat().st_mtime == original_mtime

    output = " ".join(printed)
    assert "no está" in output or "warning" in output.lower()


def test_disconnect_invalid_url(tmp_path, monkeypatch):
    """Non-https URL prints error without reading the peers file at all."""
    import zana.commands.aeon as aeon_mod

    # Point _PEERS_PATH to a non-existent file so any read attempt would fail
    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    printed = []
    with patch.object(aeon_mod.console, "print") as mock_print:
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_disconnect("http://insecure.example.com")

    assert not peers_file.exists()  # file never created
    output = " ".join(printed)
    assert "error" in output.lower() or "https" in output.lower()


def test_disconnect_civic_ledger(tmp_path, monkeypatch):
    """Disconnect calls SentinelLiteDB.record with 'ZNetworkDisconnect'."""
    import zana.commands.aeon as aeon_mod

    _setup_peers(tmp_path, monkeypatch, _make_peers())

    mock_db = MagicMock()

    with (
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_disconnect(_PEER_URL)

    mock_db.record.assert_called_once()
    event_type = mock_db.record.call_args[0][0]
    assert event_type == "ZNetworkDisconnect"
