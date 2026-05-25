"""Herald v2 — Slack + Email notification channels."""

from __future__ import annotations

import hashlib
import os
import smtplib
from email.mime.text import MIMEText
from typing import Annotated
from urllib import error as urllib_error
from urllib import request as urllib_request

import typer

from zana.tui.theme import console

herald_app = typer.Typer(
    name="herald",
    help="Herald v2 — Slack and Email notification channels (One-way).",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@herald_app.callback()
def callback() -> None:
    """
    Herald Layer: One-way notifications for Slack and Email.
    For interactive, two-way bots (Telegram/Discord/WhatsApp), use: zana satellite
    """
    pass


def _audit(event_type: str, payload_hash: str) -> None:
    """Write an immutable Civic Ledger entry via SentinelLiteDB."""
    try:
        from zana.core.sentinel_lite import SentinelLiteDB

        db = SentinelLiteDB()
        db.record(event_type, payload_hash=payload_hash, civic_hash=payload_hash)
        db.close()
    except Exception:
        pass


@herald_app.command("slack")
def cmd_herald_notify_slack(
    webhook_url: Annotated[str, typer.Argument(help="Slack Incoming Webhook URL.")],
    message: Annotated[str, typer.Argument(help="Message to send to Slack.")],
) -> None:
    """Send a notification to a Slack channel via Incoming Webhook."""
    if not webhook_url.startswith("https://"):
        console.print("[error]webhook_url must start with https://[/error]")
        raise typer.Exit(1)

    import json

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib_request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=8):
            pass
        console.print("[success]✓ Slack notificado.[/success]")
    except (urllib_error.HTTPError, urllib_error.URLError) as exc:
        console.print(f"[error]Error enviando a Slack: {exc}[/error]")

    h = hashlib.sha256((webhook_url + message).encode()).hexdigest()
    _audit("HeraldSlack", payload_hash=h)


@herald_app.command("email")
def cmd_herald_notify_email(
    to_address: Annotated[str, typer.Argument(help="Recipient email address.")],
    message: Annotated[str, typer.Argument(help="Email body text.")],
    subject: Annotated[
        str, typer.Option("--subject", "-s", help="Email subject line.")
    ] = "ZANA Herald",
) -> None:
    """Send a notification email via SMTP with STARTTLS."""
    if "@" not in to_address:
        console.print("[error]to_address must contain '@'.[/error]")
        raise typer.Exit(1)

    smtp_host = os.environ.get("ZANA_SMTP_HOST", "")
    if not smtp_host:
        console.print("[error]ZANA_SMTP_HOST env var is required.[/error]")
        raise typer.Exit(1)

    smtp_port = int(os.environ.get("ZANA_SMTP_PORT", "587"))

    smtp_user = os.environ.get("ZANA_SMTP_USER", "")
    if not smtp_user:
        console.print("[error]ZANA_SMTP_USER env var is required.[/error]")
        raise typer.Exit(1)

    smtp_pass = os.environ.get("ZANA_SMTP_PASS", "")
    if not smtp_pass:
        console.print("[error]ZANA_SMTP_PASS env var is required.[/error]")
        raise typer.Exit(1)

    smtp_from = os.environ.get("ZANA_SMTP_FROM", smtp_user)

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_address

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_address], msg.as_string())
        console.print(f"[success]✓ Email enviado a {to_address}.[/success]")
    except (smtplib.SMTPException, OSError) as exc:
        console.print(f"[error]Error enviando email: {exc}[/error]")

    h = hashlib.sha256((to_address + subject).encode()).hexdigest()
    _audit("HeraldEmail", payload_hash=h)
