"""
test_satellite.py — Satellite smoke tests (Sprint 9 · Issue #7)

Tests for zana satellite configure / config read-write.
No real Telegram or Discord tokens are used — HTTP calls are mocked.
All tests use tmp_path isolation for the config file.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

import zana.core.multiuser as multiuser_mod
from zana.commands.satellite import app
from zana.core.multiuser import load_satellite_config, save_satellite_config

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Redirect SATELLITE_CONFIG to a temp path for every test."""
    config_path = tmp_path / "satellite_config.json"
    monkeypatch.setattr(multiuser_mod, "SATELLITE_CONFIG", config_path)
    yield config_path


# ---------------------------------------------------------------------------
# load_satellite_config / save_satellite_config
# ---------------------------------------------------------------------------


def test_load_config_returns_empty_dict_when_missing(isolated_config):
    result = load_satellite_config()
    assert result == {}


def test_save_and_load_config_roundtrip(isolated_config):
    config = {"telegram_token": "test-token-123", "discord_token": "disc-token-456"}
    save_satellite_config(config)
    loaded = load_satellite_config()
    assert loaded["telegram_token"] == "test-token-123"
    assert loaded["discord_token"] == "disc-token-456"


def test_save_config_creates_parent_directory(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "nested" / "satellite_config.json"
    monkeypatch.setattr(multiuser_mod, "SATELLITE_CONFIG", nested)
    save_satellite_config({"telegram_token": "tok"})
    assert nested.exists()


def test_load_config_returns_empty_on_corrupt_json(isolated_config):
    isolated_config.write_text("{ not valid json }")
    result = load_satellite_config()
    assert result == {}


# ---------------------------------------------------------------------------
# configure command — Discord (no HTTP validation)
# ---------------------------------------------------------------------------


def test_configure_discord_writes_token(isolated_config):
    result = runner.invoke(app, ["configure", "discord", "disc-token-xyz"])
    assert result.exit_code == 0
    config = load_satellite_config()
    assert config.get("discord_token") == "disc-token-xyz"


def test_configure_discord_uppercase_normalized(isolated_config):
    result = runner.invoke(app, ["configure", "DISCORD", "disc-upper-token"])
    assert result.exit_code == 0
    config = load_satellite_config()
    assert config.get("discord_token") == "disc-upper-token"


def test_configure_invalid_platform_exits_nonzero(isolated_config):
    result = runner.invoke(app, ["configure", "slack", "some-token"])
    assert result.exit_code != 0


def test_configure_preserves_existing_tokens(isolated_config):
    save_satellite_config({"telegram_token": "existing-tg-token"})
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"username": "bot"}}
        mock_get.return_value = mock_response
        result = runner.invoke(app, ["configure", "telegram", "new-tg-token"])
    config = load_satellite_config()
    assert config.get("telegram_token") == "new-tg-token"


# ---------------------------------------------------------------------------
# configure command — Telegram (mocked HTTP)
# ---------------------------------------------------------------------------


def test_configure_telegram_valid_token_succeeds(isolated_config):
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"username": "mybot"}}
        mock_get.return_value = mock_response
        result = runner.invoke(app, ["configure", "telegram", "valid-bot-token"])

    assert result.exit_code == 0
    config = load_satellite_config()
    assert config.get("telegram_token") == "valid-bot-token"


def test_configure_telegram_invalid_token_exits_nonzero(isolated_config):
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False}
        mock_get.return_value = mock_response
        result = runner.invoke(app, ["configure", "telegram", "bad-token"])

    assert result.exit_code != 0
    config = load_satellite_config()
    assert "telegram_token" not in config


def test_configure_telegram_network_error_exits_nonzero(isolated_config):
    with patch("httpx.get", side_effect=Exception("Network unreachable")):
        result = runner.invoke(app, ["configure", "telegram", "any-token"])
    assert result.exit_code != 0
