"""
test_herald_v2.py — Sprint 20 · Herald v2

Coverage for Slack and Email notification channels.
All tests use unittest.mock.patch — no real HTTP or SMTP calls are made.

Resolves: https://github.com/Kemquiros/zana-core/issues/71
"""

from __future__ import annotations

import json
import os
import smtplib
from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import Exit as ClickExit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_WEBHOOK = "https://hooks.slack.com/services/T00/B00/abc"
_VALID_EMAIL = "test@example.com"
_SMTP_ENV = {
    "ZANA_SMTP_HOST": "smtp.example.com",
    "ZANA_SMTP_PORT": "587",
    "ZANA_SMTP_USER": "user@example.com",
    "ZANA_SMTP_PASS": "secret",
    "ZANA_SMTP_FROM": "from@example.com",
}


def _import_commands():
    """Return (cmd_slack, cmd_email) — re-imported fresh each call."""
    import importlib

    import zana.commands.herald as mod

    importlib.reload(mod)
    return mod.cmd_herald_notify_slack, mod.cmd_herald_notify_email


def _make_smtp_mock():
    """Build a context-manager-compatible SMTP mock pair (cls, instance)."""
    instance = MagicMock()
    cls = MagicMock(return_value=instance)
    cls.return_value.__enter__ = lambda s: instance
    cls.return_value.__exit__ = MagicMock(return_value=False)
    return cls, instance


def _make_urlopen_mock():
    """Build a context-manager-compatible urlopen mock."""
    response = MagicMock()
    response.__enter__ = lambda s: s
    response.__exit__ = MagicMock(return_value=False)
    return response


# ---------------------------------------------------------------------------
# Slack tests
# ---------------------------------------------------------------------------


class TestSlackNotify:
    def test_slack_success(self):
        """urlopen is called with correct URL and JSON body on success."""
        cmd_slack, _ = _import_commands()
        mock_response = _make_urlopen_mock()

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            cmd_slack(_VALID_WEBHOOK, "hello world")

        assert mock_open.called
        req_arg = mock_open.call_args[0][0]
        assert req_arg.full_url == _VALID_WEBHOOK
        body = json.loads(req_arg.data)
        assert body["text"] == "hello world"

    def test_slack_invalid_url_no_call(self):
        """urlopen is NOT called when webhook_url does not start with https://."""
        cmd_slack, _ = _import_commands()
        with patch("urllib.request.urlopen") as mock_open, pytest.raises(ClickExit):
            cmd_slack("http://not-secure.example.com", "msg")
        mock_open.assert_not_called()

    def test_slack_network_error(self):
        """A URLError is caught and an error message is printed — no exception raised."""
        import urllib.error

        cmd_slack, _ = _import_commands()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            # Must not raise
            cmd_slack(_VALID_WEBHOOK, "msg")

    def test_slack_civic_ledger_written(self):
        """SentinelLiteDB.record is called with event_type='HeraldSlack'."""
        cmd_slack, _ = _import_commands()
        mock_db = MagicMock()
        mock_response = _make_urlopen_mock()

        with (
            patch("urllib.request.urlopen", return_value=mock_response),
            patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        ):
            cmd_slack(_VALID_WEBHOOK, "audit-test")

        mock_db.record.assert_called_once()
        event_type_used = mock_db.record.call_args[0][0]
        assert event_type_used == "HeraldSlack"

    def test_slack_message_in_payload(self):
        """The message content appears verbatim in the JSON body posted to Slack."""
        cmd_slack, _ = _import_commands()
        secret_msg = "ZANA_DEPLOY_COMPLETE_42"
        mock_response = _make_urlopen_mock()

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            cmd_slack(_VALID_WEBHOOK, secret_msg)

        req_arg = mock_open.call_args[0][0]
        body = json.loads(req_arg.data)
        assert body["text"] == secret_msg


# ---------------------------------------------------------------------------
# Email tests
# ---------------------------------------------------------------------------


class TestEmailNotify:
    def test_email_success(self):
        """starttls(), login(), and sendmail() are all called on success."""
        _, cmd_email = _import_commands()
        smtp_cls, smtp_inst = _make_smtp_mock()

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            cmd_email(_VALID_EMAIL, "hello email")

        smtp_inst.starttls.assert_called_once()
        smtp_inst.login.assert_called_once_with(
            _SMTP_ENV["ZANA_SMTP_USER"], _SMTP_ENV["ZANA_SMTP_PASS"]
        )
        assert smtp_inst.sendmail.called

    def test_email_invalid_address_no_smtp(self):
        """smtplib.SMTP is NOT instantiated when to_address has no '@'."""
        _, cmd_email = _import_commands()
        with patch("smtplib.SMTP") as mock_smtp, pytest.raises(ClickExit):
            cmd_email("notanemail", "body")
        mock_smtp.assert_not_called()

    def test_email_missing_smtp_host(self):
        """Error is printed and SMTP is not called when ZANA_SMTP_HOST is absent."""
        _, cmd_email = _import_commands()
        env = {k: v for k, v in _SMTP_ENV.items() if k != "ZANA_SMTP_HOST"}
        os.environ.pop("ZANA_SMTP_HOST", None)
        with (
            patch.dict("os.environ", env, clear=False),
            patch("smtplib.SMTP") as mock_smtp,
            pytest.raises(ClickExit),
        ):
            cmd_email(_VALID_EMAIL, "body")
        mock_smtp.assert_not_called()

    def test_email_missing_smtp_user(self):
        """Error is printed and SMTP is not called when ZANA_SMTP_USER is absent."""
        _, cmd_email = _import_commands()
        env = {k: v for k, v in _SMTP_ENV.items() if k != "ZANA_SMTP_USER"}
        env["ZANA_SMTP_HOST"] = "smtp.example.com"
        os.environ.pop("ZANA_SMTP_USER", None)
        with (
            patch.dict("os.environ", env, clear=False),
            patch("smtplib.SMTP") as mock_smtp,
            pytest.raises(ClickExit),
        ):
            cmd_email(_VALID_EMAIL, "body")
        mock_smtp.assert_not_called()

    def test_email_smtp_exception(self):
        """SMTPException is caught and an error message is printed — no raise."""
        _, cmd_email = _import_commands()
        smtp_cls, smtp_inst = _make_smtp_mock()
        smtp_inst.starttls = MagicMock()
        smtp_inst.login = MagicMock(
            side_effect=smtplib.SMTPAuthenticationError(535, b"Auth failed")
        )

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            # Must not raise
            cmd_email(_VALID_EMAIL, "body")

    def test_email_civic_ledger_written(self):
        """SentinelLiteDB.record is called with event_type='HeraldEmail'."""
        _, cmd_email = _import_commands()
        mock_db = MagicMock()
        smtp_cls, _ = _make_smtp_mock()

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
            patch("zana.core.sentinel_lite.SentinelLiteDB", return_value=mock_db),
        ):
            cmd_email(_VALID_EMAIL, "audit-body")

        mock_db.record.assert_called_once()
        event_type_used = mock_db.record.call_args[0][0]
        assert event_type_used == "HeraldEmail"

    def test_email_default_subject(self):
        """Subject defaults to 'ZANA Herald' when not supplied."""
        _, cmd_email = _import_commands()
        smtp_cls, smtp_inst = _make_smtp_mock()

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            cmd_email(_VALID_EMAIL, "body")  # no subject arg

        raw_message = smtp_inst.sendmail.call_args[0][2]
        assert "ZANA Herald" in raw_message

    def test_email_custom_subject(self):
        """A custom subject is passed through to the email headers."""
        _, cmd_email = _import_commands()
        smtp_cls, smtp_inst = _make_smtp_mock()
        custom_subj = "Deployment Alert: v3.99.0"

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            cmd_email(_VALID_EMAIL, "body", custom_subj)

        raw_message = smtp_inst.sendmail.call_args[0][2]
        assert custom_subj in raw_message

    def test_email_from_defaults_to_user(self):
        """ZANA_SMTP_FROM defaults to ZANA_SMTP_USER when not set."""
        _, cmd_email = _import_commands()
        smtp_cls, smtp_inst = _make_smtp_mock()
        env = {k: v for k, v in _SMTP_ENV.items() if k != "ZANA_SMTP_FROM"}
        os.environ.pop("ZANA_SMTP_FROM", None)

        with (
            patch.dict("os.environ", env, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            cmd_email(_VALID_EMAIL, "body")

        from_addr = smtp_inst.sendmail.call_args[0][0]
        assert from_addr == _SMTP_ENV["ZANA_SMTP_USER"]

    def test_email_starttls_always_called(self):
        """STARTTLS is called before login — plaintext auth is never used."""
        _, cmd_email = _import_commands()
        call_order: list[str] = []
        smtp_cls, smtp_inst = _make_smtp_mock()
        smtp_inst.starttls.side_effect = lambda: call_order.append("starttls")
        smtp_inst.login.side_effect = lambda u, p: call_order.append("login")

        with (
            patch.dict("os.environ", _SMTP_ENV, clear=False),
            patch("smtplib.SMTP", smtp_cls),
        ):
            cmd_email(_VALID_EMAIL, "body")

        assert "starttls" in call_order, "starttls must be called"
        assert "login" in call_order, "login must be called"
        assert call_order.index("starttls") < call_order.index("login"), (
            "starttls must be called BEFORE login"
        )
