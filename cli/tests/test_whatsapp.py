"""
test_whatsapp.py — WhatsApp Herald channel tests (Sprint 12, Issue #34)

Covers: WhatsAppBot webhook handling, message routing, send_message,
        verify_webhook, validate_token, ZSM fallback, gateway forwarding,
        satellite configure command for whatsapp platform.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner
from zana.commands.satellite import app as satellite_app
from zana.core.satellite.whatsapp_bot import WhatsAppBot, validate_whatsapp_token_sync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

cli_runner = CliRunner()


def _make_bot(
    phone_number_id: str = "12345",
    access_token: str = "test_token",
    gateway_url: str | None = None,
    verify_token: str = "zana_wa_verify",
) -> Any:
    registry = MagicMock()
    registry.get.return_value = MagicMock(language="en", archetype="warrior")
    return WhatsAppBot(
        phone_number_id=phone_number_id,
        access_token=access_token,
        registry=registry,
        host_aeon_name="ZANA",
        gateway_url=gateway_url,
        verify_token=verify_token,
    )


def _text_msg(wa_id: str = "5491100000001", body: str = "hello") -> dict:
    return {"type": "text", "from": wa_id, "text": {"body": body}}


def _webhook_payload(msg: dict) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {"messages": [msg]},
                    }
                ]
            }
        ]
    }


# ---------------------------------------------------------------------------
# verify_webhook
# ---------------------------------------------------------------------------


def test_verify_webhook_returns_challenge_on_match():
    bot = _make_bot()
    result = bot.verify_webhook("subscribe", "abc123", "zana_wa_verify")
    assert result == "abc123"


def test_verify_webhook_returns_none_wrong_token():
    bot = _make_bot()
    assert bot.verify_webhook("subscribe", "abc123", "wrong_token") is None


def test_verify_webhook_returns_none_wrong_mode():
    bot = _make_bot()
    assert bot.verify_webhook("unsubscribe", "abc123", "zana_wa_verify") is None


def test_verify_webhook_custom_token():
    bot = _make_bot(verify_token="my_custom_token")
    assert (
        bot.verify_webhook("subscribe", "challenge_xyz", "my_custom_token")
        == "challenge_xyz"
    )


# ---------------------------------------------------------------------------
# handle_webhook — routing
# ---------------------------------------------------------------------------


def test_handle_webhook_routes_text_message():
    bot = _make_bot()
    payload = _webhook_payload(_text_msg())
    with (
        patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send,
        patch.object(bot, "_zsm_respond", return_value="pong"),
    ):
        asyncio.run(bot.handle_webhook(payload))
    mock_send.assert_awaited_once()


def test_handle_webhook_ignores_non_text():
    bot = _make_bot()
    payload = _webhook_payload({"type": "image", "from": "5491100000001"})
    with patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send:
        asyncio.run(bot.handle_webhook(payload))
    mock_send.assert_not_awaited()


def test_handle_webhook_ignores_reaction():
    bot = _make_bot()
    payload = _webhook_payload({"type": "reaction", "from": "5491100000001"})
    with patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send:
        asyncio.run(bot.handle_webhook(payload))
    mock_send.assert_not_awaited()


def test_handle_webhook_empty_body_ignored():
    bot = _make_bot()
    msg = {"type": "text", "from": "5491100000001", "text": {"body": "   "}}
    payload = _webhook_payload(msg)
    with patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send:
        asyncio.run(bot.handle_webhook(payload))
    mock_send.assert_not_awaited()


def test_handle_webhook_empty_entry():
    bot = _make_bot()
    asyncio.run(bot.handle_webhook({}))  # must not raise


def test_handle_webhook_registers_new_user():
    bot = _make_bot()
    bot._registry.get.return_value = None
    payload = _webhook_payload(_text_msg(wa_id="new_user_001"))
    with (
        patch.object(bot, "send_message", new_callable=AsyncMock),
        patch.object(bot, "_zsm_respond", return_value="hi"),
    ):
        asyncio.run(bot.handle_webhook(payload))
    bot._registry.register.assert_called_once_with(
        "whatsapp", "new_user_001", "new_user_001", lang="en"
    )


def test_handle_webhook_touches_existing_user():
    bot = _make_bot()
    payload = _webhook_payload(_text_msg(wa_id="existing_user"))
    with (
        patch.object(bot, "send_message", new_callable=AsyncMock),
        patch.object(bot, "_zsm_respond", return_value="hi"),
    ):
        asyncio.run(bot.handle_webhook(payload))
    bot._registry.touch.assert_called_once_with("whatsapp", "existing_user")


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


def test_send_message_posts_to_graph_api():
    bot = _make_bot()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        asyncio.run(bot.send_message("5491100000001", "Hello!"))

    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.call_args
    assert "12345/messages" in call_kwargs.args[0]
    assert call_kwargs.kwargs["json"]["text"]["body"] == "Hello!"
    assert "Bearer test_token" in call_kwargs.kwargs["headers"]["Authorization"]


def test_send_message_truncates_long_content():
    bot = _make_bot()
    long_text = "x" * 5000
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        asyncio.run(bot.send_message("5491100000001", long_text))

    sent_body = mock_client.post.call_args.kwargs["json"]["text"]["body"]
    assert len(sent_body) <= 4096
    assert sent_body.endswith("...")


def test_send_message_swallows_network_error():
    bot = _make_bot()
    with patch("httpx.AsyncClient", side_effect=Exception("network error")):
        asyncio.run(bot.send_message("5491100000001", "hi"))  # must not raise


# ---------------------------------------------------------------------------
# _zsm_respond (fallback)
# ---------------------------------------------------------------------------


def test_zsm_respond_returns_string():
    bot = _make_bot()
    user = MagicMock(archetype="warrior")
    with patch("zana.core.zsm.ZSMEngine") as mock_engine_cls:
        mock_engine_cls.return_value.respond_text.return_value = "ZSM reply"
        result = bot._zsm_respond("hello", user, "en")
    assert result == "ZSM reply"


def test_zsm_respond_fallback_on_error():
    bot = _make_bot()
    user = MagicMock(archetype="warrior")
    with patch("zana.core.zsm.ZSMEngine", side_effect=Exception("fail")):
        result = bot._zsm_respond("hello", user, "en")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# _query_gateway
# ---------------------------------------------------------------------------


def test_query_gateway_returns_none_when_no_url():
    bot = _make_bot(gateway_url=None)
    user = MagicMock(user_id="u1", language="en")
    result = asyncio.run(bot._query_gateway("hello", user))
    assert result is None


def test_query_gateway_returns_response_on_200():
    bot = _make_bot(gateway_url="http://localhost:8080")
    user = MagicMock(user_id="u1", language="en")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"response": "gateway reply"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(bot._query_gateway("hello", user))

    assert result == "gateway reply"


def test_query_gateway_returns_none_on_non_200():
    bot = _make_bot(gateway_url="http://localhost:8080")
    user = MagicMock(user_id="u1", language="en")
    mock_resp = MagicMock(status_code=500)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(bot._query_gateway("hello", user))

    assert result is None


def test_query_gateway_returns_none_on_exception():
    bot = _make_bot(gateway_url="http://localhost:8080")
    user = MagicMock(user_id="u1", language="en")
    with patch("httpx.AsyncClient", side_effect=Exception("timeout")):
        result = asyncio.run(bot._query_gateway("hello", user))
    assert result is None


# ---------------------------------------------------------------------------
# validate_token (static)
# ---------------------------------------------------------------------------


def test_validate_token_returns_true_on_valid():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"id": "12345"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(WhatsAppBot.validate_token("valid_token"))

    assert result is True


def test_validate_token_returns_false_on_401():
    mock_resp = MagicMock(status_code=401)
    mock_resp.json.return_value = {"error": "invalid"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(WhatsAppBot.validate_token("bad_token"))

    assert result is False


def test_validate_token_returns_false_on_network_error():
    with patch("httpx.AsyncClient", side_effect=Exception("network")):
        result = asyncio.run(WhatsAppBot.validate_token("any_token"))

    assert result is False


def test_validate_whatsapp_token_sync_wrapper():
    with patch(
        "zana.core.satellite.whatsapp_bot.WhatsAppBot.validate_token",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = validate_whatsapp_token_sync("a_token")

    assert result is True


# ---------------------------------------------------------------------------
# satellite configure command — whatsapp platform
# ---------------------------------------------------------------------------


def test_configure_whatsapp_requires_phone_number_id():
    result = cli_runner.invoke(satellite_app, ["configure", "whatsapp", "mytoken"])
    assert result.exit_code != 0
    assert (
        "phone-number-id" in result.output.lower()
        or "phone_number_id" in result.output.lower()
    )


def test_configure_whatsapp_invalid_token(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".zana").mkdir()

    with patch(
        "zana.core.satellite.whatsapp_bot.validate_whatsapp_token_sync",
        return_value=False,
    ):
        result = cli_runner.invoke(
            satellite_app,
            ["configure", "whatsapp", "badtoken", "--phone-number-id", "12345"],
        )
    assert result.exit_code != 0


def test_configure_whatsapp_saves_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".zana").mkdir()

    with (
        patch(
            "zana.core.satellite.whatsapp_bot.validate_whatsapp_token_sync",
            return_value=True,
        ),
        patch("zana.core.multiuser.load_satellite_config", return_value={}),
        patch("zana.core.multiuser.save_satellite_config") as mock_save,
    ):
        result = cli_runner.invoke(
            satellite_app,
            ["configure", "whatsapp", "validtoken", "--phone-number-id", "99999"],
        )

    assert result.exit_code == 0
    saved_config = mock_save.call_args[0][0]
    assert saved_config["whatsapp_token"] == "validtoken"
    assert saved_config["whatsapp_phone_number_id"] == "99999"


def test_configure_rejects_unknown_platform():
    result = cli_runner.invoke(satellite_app, ["configure", "slack", "token123"])
    assert result.exit_code != 0
