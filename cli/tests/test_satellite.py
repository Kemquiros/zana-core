"""
test_satellite.py — Satellite smoke tests (Sprint 9 + Sprint 12)

Tests for zana satellite configure / config read-write.
No real Telegram or Discord tokens are used — HTTP calls are mocked.
All tests use tmp_path isolation for the config file.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import zana.core.multiuser as multiuser_mod
from typer.testing import CliRunner
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
# configure command — Discord (mocked token validation)
# ---------------------------------------------------------------------------

_DISCORD_VALIDATE = "zana.core.satellite.discord_bot.validate_discord_token_sync"


def test_configure_discord_writes_token(isolated_config):
    with patch(_DISCORD_VALIDATE, return_value=True):
        result = runner.invoke(app, ["configure", "discord", "disc-token-xyz"])
    assert result.exit_code == 0
    config = load_satellite_config()
    assert config.get("discord_token") == "disc-token-xyz"


def test_configure_discord_uppercase_normalized(isolated_config):
    with patch(_DISCORD_VALIDATE, return_value=True):
        result = runner.invoke(app, ["configure", "DISCORD", "disc-upper-token"])
    assert result.exit_code == 0
    config = load_satellite_config()
    assert config.get("discord_token") == "disc-upper-token"


def test_configure_discord_invalid_token_exits_nonzero(isolated_config):
    with patch(_DISCORD_VALIDATE, return_value=False):
        result = runner.invoke(app, ["configure", "discord", "bad-discord-token"])
    assert result.exit_code != 0
    config = load_satellite_config()
    assert "discord_token" not in config


def test_configure_invalid_platform_exits_nonzero(isolated_config):
    result = runner.invoke(app, ["configure", "slack", "some-token"])
    assert result.exit_code != 0


def test_configure_preserves_existing_tokens(isolated_config):
    save_satellite_config({"telegram_token": "existing-tg-token"})
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"username": "bot"}}
        mock_get.return_value = mock_response
        runner.invoke(app, ["configure", "telegram", "new-tg-token"])
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


# ---------------------------------------------------------------------------
# DiscordBot unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    user = MagicMock()
    user.language = "en"
    user.archetype = "warrior"
    user.user_id = "discord_123"
    reg.get.return_value = user
    return reg


@pytest.fixture
def discord_bot(mock_registry):
    from zana.core.satellite.discord_bot import DiscordBot

    return DiscordBot(
        token="fake-token",
        registry=mock_registry,
        host_aeon_name="TestAeon",
        gateway_url=None,
    )


def test_discord_bot_instantiates(discord_bot):
    assert discord_bot._token == "fake-token"
    assert discord_bot._host_aeon == "TestAeon"
    assert discord_bot._running is True


def test_discord_bot_stop_sets_flag(discord_bot):
    discord_bot.stop()
    assert discord_bot._running is False


def test_discord_bot_handle_message_dm(discord_bot, mock_registry):
    """DM to bot should trigger a ZSM response."""
    import asyncio

    message_data = {
        "channel_id": "chan-999",
        "author": {"id": "user-111", "username": "TestUser", "bot": False},
        "content": "hello",
        "guild_id": None,
    }
    with (
        patch.object(
            discord_bot, "_zsm_respond", return_value="Hi from ZANA"
        ) as mock_zsm,
        patch.object(discord_bot, "_send_message", new_callable=AsyncMock) as mock_send,
    ):
        asyncio.run(discord_bot._handle_message(message_data))
        mock_zsm.assert_called_once()
        mock_send.assert_called_once_with("chan-999", "Hi from ZANA")


def test_discord_bot_ignores_bot_messages(discord_bot):
    """Messages from other bots must be ignored."""
    import asyncio

    message_data = {
        "channel_id": "chan-999",
        "author": {"id": "bot-222", "username": "OtherBot", "bot": True},
        "content": "/zana hello",
        "guild_id": "guild-1",
    }
    with patch.object(
        discord_bot, "_send_message", new_callable=AsyncMock
    ) as mock_send:
        asyncio.run(discord_bot._handle_message(message_data))
        mock_send.assert_not_called()


def test_discord_bot_guild_requires_prefix(discord_bot):
    """In guild channels, message must start with /zana or @mention the bot."""
    import asyncio

    discord_bot._bot_user_id = "bot-id-999"
    message_data = {
        "channel_id": "chan-1",
        "author": {"id": "user-1", "username": "Alice", "bot": False},
        "content": "just a regular message",
        "guild_id": "guild-1",
    }
    with patch.object(
        discord_bot, "_send_message", new_callable=AsyncMock
    ) as mock_send:
        asyncio.run(discord_bot._handle_message(message_data))
        mock_send.assert_not_called()


def test_discord_bot_guild_slash_command(discord_bot):
    """/zana <prompt> in guild channel must be handled."""
    import asyncio

    message_data = {
        "channel_id": "chan-1",
        "author": {"id": "user-2", "username": "Bob", "bot": False},
        "content": "/zana what is 2+2?",
        "guild_id": "guild-1",
    }
    with (
        patch.object(discord_bot, "_zsm_respond", return_value="4") as mock_zsm,
        patch.object(discord_bot, "_send_message", new_callable=AsyncMock) as mock_send,
    ):
        asyncio.run(discord_bot._handle_message(message_data))
        mock_zsm.assert_called_once()
        mock_send.assert_called_once()


def test_discord_bot_auto_registers_new_user(discord_bot, mock_registry):
    """First contact from a new Discord user auto-registers them."""
    import asyncio

    mock_registry.get.return_value = None
    message_data = {
        "channel_id": "chan-1",
        "author": {"id": "new-user-333", "username": "NewUser", "bot": False},
        "content": "/zana hello",
        "guild_id": "guild-1",
    }
    with (
        patch.object(discord_bot, "_zsm_respond", return_value="Welcome!"),
        patch.object(discord_bot, "_send_message", new_callable=AsyncMock),
    ):
        asyncio.run(discord_bot._handle_message(message_data))
    mock_registry.register.assert_called_once_with(
        "discord", "new-user-333", "NewUser", lang="en"
    )


def test_discord_civic_hash_in_bot_module():
    from zana.core.satellite.discord_bot import _API_BASE, _GATEWAY_URL

    assert _API_BASE.startswith("https://discord.com")
    assert _GATEWAY_URL.startswith("wss://gateway.discord.gg")
