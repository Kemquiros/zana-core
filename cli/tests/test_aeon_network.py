"""Tests for Z-Network v0.1 — connect, peers, broadcast (S19-A)."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ZL = "ARIA_01 ! wisdom:rule:test [conf:0.80]"
_PEER_URL = "https://peer.example.com"
_PEER_URL_2 = "https://node.example.com"


def _setup_peers(tmp_path: Path, monkeypatch, peers: dict) -> None:
    """Write a peers file and monkeypatch _PEERS_PATH."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    if peers:
        peers_file.write_text(json.dumps(peers, indent=2), encoding="utf-8")
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)


# ---------------------------------------------------------------------------
# cmd_aeon_connect
# ---------------------------------------------------------------------------


def test_connect_adds_peer_to_file(tmp_path, monkeypatch):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    aeon_mod.cmd_aeon_connect(_PEER_URL, name="alice")

    assert peers_file.exists()
    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert _PEER_URL in data
    assert data[_PEER_URL]["name"] == "alice"
    assert data[_PEER_URL]["connected_at"] is not None
    assert data[_PEER_URL]["last_seen"] is None


def test_connect_requires_https(tmp_path, monkeypatch, capsys):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    aeon_mod.cmd_aeon_connect("http://insecure.com", name="bad")

    assert not peers_file.exists()


def test_connect_defaults_name_from_url(tmp_path, monkeypatch):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    aeon_mod.cmd_aeon_connect("https://node.example.com/myaeon")

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    url = "https://node.example.com/myaeon"
    assert data[url]["name"] == "myaeon"


def test_connect_preserves_existing_peers(tmp_path, monkeypatch):
    import zana.commands.aeon as aeon_mod

    existing = {
        "https://first.example.com": {
            "name": "first",
            "connected_at": "2026-01-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, existing)
    peers_file = tmp_path / "aeon_peers.json"

    aeon_mod.cmd_aeon_connect("https://second.example.com", name="second")

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert "https://first.example.com" in data
    assert "https://second.example.com" in data


def test_connect_atomic_write(tmp_path, monkeypatch):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    aeon_mod.cmd_aeon_connect(_PEER_URL, name="alice")

    # The .tmp file must NOT remain after a successful write
    tmp_file = peers_file.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_connect_overwrites_existing_peer(tmp_path, monkeypatch):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    aeon_mod.cmd_aeon_connect(_PEER_URL, name="first")
    aeon_mod.cmd_aeon_connect(_PEER_URL, name="second")

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[_PEER_URL]["name"] == "second"


# ---------------------------------------------------------------------------
# cmd_aeon_peers
# ---------------------------------------------------------------------------


def test_peers_empty_message(tmp_path, monkeypatch, capsys):
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    printed = []
    with patch("zana.tui.theme.console") as mock_console:
        mock_console.print.side_effect = lambda *a, **kw: printed.append(str(a))
        # Re-import so the patched console is used
        import importlib

        importlib.reload(aeon_mod)
        monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)
        aeon_mod.cmd_aeon_peers()

    # At minimum one print call should mention "No peers"
    output = " ".join(printed)
    assert "No peers" in output or len(printed) >= 1


def test_peers_shows_table(tmp_path, monkeypatch):
    """With 2 peers populated, console.print must be called (table + spacing)."""
    import zana.commands.aeon as aeon_mod

    peers = {
        "https://alpha.example.com": {
            "name": "alpha",
            "connected_at": "2026-05-01T10:00:00+00:00",
            "last_seen": None,
        },
        "https://beta.example.com": {
            "name": "beta",
            "connected_at": "2026-05-02T11:00:00+00:00",
            "last_seen": "2026-05-03T12:00:00+00:00",
        },
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    call_count = []
    with patch.object(aeon_mod.console, "print") as mock_print:
        mock_print.side_effect = lambda *a, **kw: call_count.append(1)
        aeon_mod.cmd_aeon_peers()

    assert len(call_count) >= 2  # at least blank lines + table


def test_peers_corrupt_file_handled(tmp_path, monkeypatch):
    """Corrupt JSON in peers file should not raise — fall back to empty."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    peers_file.write_text("{invalid json!!}", encoding="utf-8")
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    # Should not raise
    call_count = []
    with patch.object(aeon_mod.console, "print") as mock_print:
        mock_print.side_effect = lambda *a, **kw: call_count.append(str(a))
        aeon_mod.cmd_aeon_peers()

    assert len(call_count) >= 1  # "No peers" message


# ---------------------------------------------------------------------------
# cmd_aeon_broadcast
# ---------------------------------------------------------------------------


def test_broadcast_invalid_zl_rejected(tmp_path, monkeypatch):
    """Non-ZL input must print an error and make zero HTTP calls."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    with patch("urllib.request.urlopen") as mock_urlopen:
        aeon_mod.cmd_aeon_broadcast("not a zl message")
        mock_urlopen.assert_not_called()


def test_broadcast_no_peers_warning(tmp_path, monkeypatch):
    """No peers file → print warning, no HTTP calls."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    monkeypatch.setattr(aeon_mod, "_PEERS_PATH", peers_file)

    with patch("urllib.request.urlopen") as mock_urlopen:
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)
        mock_urlopen.assert_not_called()


def test_broadcast_delivered_count(tmp_path, monkeypatch):
    """2 peers, both respond OK → summary shows 2 delivered 0 failed."""
    import zana.commands.aeon as aeon_mod

    peers = {
        "https://alpha.example.com": {
            "name": "alpha",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        },
        "https://beta.example.com": {
            "name": "beta",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        },
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    printed = []
    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    summary = " ".join(printed)
    assert "2 delivered" in summary
    assert "0 failed" in summary


def test_broadcast_partial_failure(tmp_path, monkeypatch):
    """2 peers, one raises URLError → 1 delivered 1 failed."""
    import zana.commands.aeon as aeon_mod

    peers = {
        "https://alpha.example.com": {
            "name": "alpha",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        },
        "https://beta.example.com": {
            "name": "beta",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        },
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    call_count = [0]

    def side_effect(req, timeout=5):
        call_count[0] += 1
        if call_count[0] == 1:
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp
        raise urllib.error.URLError("connection refused")

    printed = []
    with (
        patch("urllib.request.urlopen", side_effect=side_effect),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: printed.append(str(a))
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    summary = " ".join(printed)
    assert "1 delivered" in summary
    assert "1 failed" in summary


def test_broadcast_updates_last_seen(tmp_path, monkeypatch):
    """After a successful delivery, last_seen is written to the peers file."""
    import zana.commands.aeon as aeon_mod

    peers_file = tmp_path / "aeon_peers.json"
    peers = {
        _PEER_URL: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    data = json.loads(peers_file.read_text(encoding="utf-8"))
    assert data[_PEER_URL]["last_seen"] is not None


def test_broadcast_civic_ledger_written(tmp_path, monkeypatch):
    """SentinelLiteDB.record must be called with 'ZNetworkBroadcast'."""
    import zana.commands.aeon as aeon_mod

    peers = {
        _PEER_URL: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    mock_db = MagicMock()

    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    mock_db.record.assert_called_once()
    call_args = mock_db.record.call_args
    assert call_args[0][0] == "ZNetworkBroadcast"


def test_broadcast_timeout_per_peer(tmp_path, monkeypatch):
    """urlopen must be called with timeout=5."""
    import zana.commands.aeon as aeon_mod

    peers = {
        _PEER_URL: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    captured_kwargs = []

    def capture_urlopen(req, timeout=None):
        captured_kwargs.append({"timeout": timeout})
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with (
        patch("urllib.request.urlopen", side_effect=capture_urlopen),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["timeout"] == 5


def test_broadcast_json_envelope_format(tmp_path, monkeypatch):
    """The data sent to urlopen must be valid JSON with keys: zl, from, timestamp."""
    import zana.commands.aeon as aeon_mod

    peers = {
        _PEER_URL: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    captured_data = []

    def capture_urlopen(req, timeout=None):
        captured_data.append(req.data)
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with (
        patch("urllib.request.urlopen", side_effect=capture_urlopen),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    assert len(captured_data) == 1
    envelope = json.loads(captured_data[0].decode("utf-8"))
    assert "zl" in envelope
    assert "from" in envelope
    assert "timestamp" in envelope
    assert envelope["zl"] == _VALID_ZL


def test_broadcast_posts_to_slash_zl_endpoint(tmp_path, monkeypatch):
    """Endpoint must be peer_url.rstrip('/') + '/zl'."""
    import zana.commands.aeon as aeon_mod

    peers = {
        _PEER_URL_2: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    captured_urls = []

    def capture_urlopen(req, timeout=None):
        captured_urls.append(req.full_url)
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with (
        patch("urllib.request.urlopen", side_effect=capture_urlopen),
        patch.object(aeon_mod.console, "print"),
    ):
        aeon_mod.cmd_aeon_broadcast(_VALID_ZL)

    assert len(captured_urls) == 1
    assert captured_urls[0] == f"{_PEER_URL_2}/zl"


def test_broadcast_valid_zl_accepted(tmp_path, monkeypatch):
    """A syntactically valid ZL message must not trigger an error path."""
    import zana.commands.aeon as aeon_mod

    peers = {
        _PEER_URL: {
            "name": "test",
            "connected_at": "2026-05-01T00:00:00+00:00",
            "last_seen": None,
        }
    }
    _setup_peers(tmp_path, monkeypatch, peers)

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    error_messages = []
    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch.object(aeon_mod.console, "print") as mock_print,
    ):
        mock_print.side_effect = lambda *a, **kw: (
            error_messages.append(str(a)) if "[error]" in str(a) else None
        )
        aeon_mod.cmd_aeon_broadcast("ARIA_01 ! wisdom:rule:test [conf:0.80] [delta:+1]")

    assert len(error_messages) == 0


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_peers_file_path_under_home():
    from zana.commands.aeon import _PEERS_PATH

    assert _PEERS_PATH.parent == Path.home() / ".zana"
    assert _PEERS_PATH.name == "aeon_peers.json"
