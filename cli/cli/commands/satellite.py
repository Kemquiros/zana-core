"""Satellite multi-user layer — Telegram / Discord."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from cli.tui.theme import console

app = typer.Typer(
    name="satellite",
    help="Satellite connectivity layer — Telegram, Discord.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

PID_FILE = Path.home() / ".zana" / "satellite.pid"


def _t(key: str, **kwargs: object) -> str:
    try:
        from cli.core.i18n import t
        from cli.core.zsm import load_env_file

        load_env_file()
        lang = os.environ.get("ZANA_LANG", "es")
        return t(key, lang=lang, **kwargs)
    except Exception:
        return key


def _read_pid() -> int | None:
    try:
        if PID_FILE.exists():
            return int(PID_FILE.read_text().strip())
    except Exception:
        pass
    return None


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


@app.command("configure")
def configure(
    platform: Annotated[str, typer.Argument(help="Platform: telegram | discord")],
    token: Annotated[str, typer.Argument(help="Bot token")],
) -> None:
    """Configure a satellite platform bot token."""
    platform = platform.lower().strip()
    if platform not in ("telegram", "discord"):
        console.print("[error]Platform must be 'telegram' or 'discord'.[/error]")
        raise typer.Exit(1)

    from cli.core.multiuser import load_satellite_config, save_satellite_config

    # Validate token
    if platform == "telegram":
        import httpx

        try:
            r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if not r.json().get("ok"):
                console.print(
                    _t(
                        "satellite.configure.invalid_token",
                        platform=platform.capitalize(),
                    )
                )
                raise typer.Exit(1)
        except Exception:
            console.print(
                _t("satellite.configure.invalid_token", platform=platform.capitalize())
            )
            raise typer.Exit(1) from None

    config = load_satellite_config()
    config[f"{platform}_token"] = token
    save_satellite_config(config)
    console.print(_t("satellite.configure.success", platform=platform.capitalize()))


@app.command("start")
def start(
    foreground: Annotated[
        bool, typer.Option("--foreground", "-f", help="Run in foreground.")
    ] = False,
) -> None:
    """Start the satellite background process."""
    from cli.core.multiuser import load_satellite_config

    config = load_satellite_config()
    if not config.get("telegram_token") and not config.get("discord_token"):
        console.print(
            "[error]No platform configured. Run: zana satellite configure telegram <token>[/error]"
        )
        raise typer.Exit(1)

    pid = _read_pid()
    if pid and _is_alive(pid):
        console.print(f"[warning]Satellite already running (PID {pid}).[/warning]")
        return

    if foreground:
        from cli.core.satellite.runner import run

        run()
        return

    proc = subprocess.Popen(
        [sys.executable, "-m", "cli.core.satellite.runner"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))
    console.print(f"[success]✓ Satellite started. PID: {proc.pid}[/success]")


@app.command("stop")
def stop() -> None:
    """Stop the satellite process."""
    pid = _read_pid()
    if not pid:
        console.print("[muted]Satellite not running.[/muted]")
        return
    if not _is_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        console.print("[muted]Satellite was already stopped.[/muted]")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        console.print(f"[success]✓ Satellite stopped (PID {pid}).[/success]")
    except Exception as exc:
        console.print(f"[error]Could not stop satellite: {exc}[/error]")


@app.command("status")
def cmd_status() -> None:
    """Show satellite status."""
    from cli.core.multiuser import UserRegistry, load_satellite_config

    config = load_satellite_config()
    pid = _read_pid()
    running = pid is not None and _is_alive(pid)
    platform = (
        "telegram"
        if config.get("telegram_token")
        else ("discord" if config.get("discord_token") else "—")
    )
    user_count = len(UserRegistry().list_all())

    if running:
        console.print(
            _t(
                "satellite.status.running",
                pid=pid,
                platform=platform.capitalize(),
                user_count=user_count,
            )
        )
    else:
        console.print(_t("satellite.status.stopped"))


@app.command("users")
def users() -> None:
    """List registered satellite users."""
    from cli.core.multiuser import UserRegistry

    all_users = UserRegistry().list_all()
    if not all_users:
        console.print(_t("satellite.users.empty"))
        return

    console.print(_t("satellite.users.header", count=len(all_users)))
    table = Table(show_header=True, header_style="header", box=None, padding=(0, 1))
    table.add_column("ID", style="muted", width=16)
    table.add_column("Platform", width=10)
    table.add_column("Aeon", style="accent", width=14)
    table.add_column("Lang", width=6)
    table.add_column("Last seen", style="muted")

    for u in all_users:
        last = u.last_seen[:10] if u.last_seen else "—"
        table.add_row(u.user_id, u.platform.capitalize(), u.aeon_name, u.language, last)

    console.print(table)


@app.command("invite")
def invite() -> None:
    """Generate an invite link for a new user."""
    import secrets

    from cli.core.multiuser import UserRegistry, load_satellite_config

    config = load_satellite_config()
    registry = UserRegistry()
    secret = secrets.token_hex(16)
    code = registry.generate_invite_code(secret)

    bot_username = ""
    if config.get("telegram_token"):
        import httpx

        try:
            r = httpx.get(
                f"https://api.telegram.org/bot{config['telegram_token']}/getMe",
                timeout=5,
            )
            if r.json().get("ok"):
                bot_username = r.json()["result"].get("username", "")
        except Exception:
            pass

    link = f"https://t.me/{bot_username}?start={code}" if bot_username else code

    console.print(_t("satellite.invite.generated", link=link))


@app.command("kick")
def kick(
    user_id: Annotated[str, typer.Argument(help="User ID to remove")],
    platform: Annotated[
        str, typer.Option("--platform", "-p", help="Platform (default: telegram)")
    ] = "telegram",
) -> None:
    """Remove a user from the satellite."""
    from cli.core.multiuser import UserRegistry

    removed = UserRegistry().remove(platform.lower(), user_id)
    if removed:
        console.print(_t("satellite.kick.success", user_id=user_id))
    else:
        console.print(_t("satellite.kick.not_found", user_id=user_id))
