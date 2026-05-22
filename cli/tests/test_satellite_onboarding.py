"""Tests for S14-2: optional satellite setup in zana init wizard."""

from unittest.mock import MagicMock, patch


def test_setup_satellite_optional_is_importable():
    """_setup_satellite_optional exists and is callable."""
    from zana.tui.onboarding import _setup_satellite_optional

    assert callable(_setup_satellite_optional)


def test_satellite_step_skipped_when_declined(monkeypatch):
    """When user declines satellite setup, no config is saved."""
    monkeypatch.setattr("zana.tui.onboarding._is_interactive", lambda: True)

    with (
        patch("zana.core.multiuser.load_satellite_config", return_value={}),
        patch("zana.core.multiuser.save_satellite_config") as mock_save,
        patch("questionary.confirm") as mock_confirm,
    ):
        mock_confirm.return_value = MagicMock(ask=lambda: False)
        from zana.tui.onboarding import _setup_satellite_optional

        _setup_satellite_optional("es")
        mock_save.assert_not_called()


def test_satellite_step_saves_telegram_token(monkeypatch):
    """When valid Telegram token provided, save_satellite_config is called."""
    monkeypatch.setattr("zana.tui.onboarding._is_interactive", lambda: True)

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"username": "test_bot"}}

    saved_config = {}

    def mock_save(config):
        saved_config.update(config)

    with (
        patch("zana.core.multiuser.load_satellite_config", return_value={}),
        patch("zana.core.multiuser.save_satellite_config", side_effect=mock_save),
        patch("questionary.confirm") as mock_confirm,
        patch("questionary.select") as mock_select,
        patch("questionary.password") as mock_password,
        patch("httpx.get", return_value=mock_response),
    ):
        mock_confirm.return_value = MagicMock(ask=lambda: True)
        mock_select.return_value = MagicMock(ask=lambda: "Telegram")
        mock_password.return_value = MagicMock(ask=lambda: "123456:ABC-DEF")
        from zana.tui.onboarding import _setup_satellite_optional

        _setup_satellite_optional("es")

    assert saved_config.get("telegram_token") == "123456:ABC-DEF"


def test_satellite_step_skips_if_already_configured(monkeypatch):
    """If satellite already configured, step is silently skipped."""
    monkeypatch.setattr("zana.tui.onboarding._is_interactive", lambda: True)

    confirm_called = []

    with (
        patch(
            "zana.core.multiuser.load_satellite_config",
            return_value={"telegram_token": "existing_token"},
        ),
        patch("questionary.confirm") as mock_confirm,
    ):
        mock_confirm.side_effect = lambda *a, **kw: (
            confirm_called.append(True) or MagicMock(ask=lambda: True)
        )
        from zana.tui.onboarding import _setup_satellite_optional

        _setup_satellite_optional("es")

    assert len(confirm_called) == 0


def test_satellite_step_invalid_token(monkeypatch):
    """Invalid Telegram token shows error, no config saved."""
    monkeypatch.setattr("zana.tui.onboarding._is_interactive", lambda: True)

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}

    saved = []

    with (
        patch("zana.core.multiuser.load_satellite_config", return_value={}),
        patch(
            "zana.core.multiuser.save_satellite_config",
            side_effect=lambda c: saved.append(c),
        ),
        patch("questionary.confirm") as mock_confirm,
        patch("questionary.select") as mock_select,
        patch("questionary.password") as mock_password,
        patch("httpx.get", return_value=mock_response),
    ):
        mock_confirm.return_value = MagicMock(ask=lambda: True)
        mock_select.return_value = MagicMock(ask=lambda: "Telegram")
        mock_password.return_value = MagicMock(ask=lambda: "bad_token")
        from zana.tui.onboarding import _setup_satellite_optional

        _setup_satellite_optional("es")

    assert len(saved) == 0


def test_satellite_step_discord_saves_token(monkeypatch):
    """Discord token is saved correctly."""
    monkeypatch.setattr("zana.tui.onboarding._is_interactive", lambda: True)

    saved_config = {}

    def mock_save(config):
        saved_config.update(config)

    with (
        patch("zana.core.multiuser.load_satellite_config", return_value={}),
        patch("zana.core.multiuser.save_satellite_config", side_effect=mock_save),
        patch("questionary.confirm") as mock_confirm,
        patch("questionary.select") as mock_select,
        patch("questionary.password") as mock_password,
    ):
        mock_confirm.return_value = MagicMock(ask=lambda: True)
        mock_select.return_value = MagicMock(ask=lambda: "Discord")
        mock_password.return_value = MagicMock(ask=lambda: "discord.token.here")
        from zana.tui.onboarding import _setup_satellite_optional

        _setup_satellite_optional("en")

    assert saved_config.get("discord_token") == "discord.token.here"
