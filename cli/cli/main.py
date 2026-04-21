from typing import Annotated, Optional

import typer
from cli.tui.theme import console, BANNER
from cli.tui.onboarding import run_onboarding, is_first_run

app = typer.Typer(
    name="zana",
    help="ZANA — Zero Autonomous Neural Architecture",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)

aeon_app = typer.Typer(
    name="aeon",
    help="Manage your Aeon fleet — specialized cognitive agents.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(aeon_app, name="aeon")


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version
        try:
            v = version("zana")
        except Exception:
            v = "2.0.0"
        console.print(f"[primary]ZANA[/primary] [muted]v{v}[/muted]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[Optional[bool], typer.Option(
        "--version", "-v", callback=_version_callback, is_eager=True,
        help="Show version and exit."
    )] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        console.print(BANNER)
        console.print("[primary]ZANA en línea. Sensores activos. ¿Qué imperio construiremos hoy?[/primary]")
        console.print("\n[muted]Run [accent]zana --help[/accent] to see available commands.[/muted]")


@app.command(help="Boot the full ZANA stack (Docker services).")
def start(
    no_detach: Annotated[bool, typer.Option("--no-detach", help="Run in foreground.")] = False,
) -> None:
    if is_first_run():
        run_onboarding()

    from cli.commands.start import cmd_start
    cmd_start(detach=not no_detach)


@app.command(help="Stop all ZANA services.")
def stop(
    volumes: Annotated[bool, typer.Option("--volumes", "-v", help="Also remove Docker volumes.")] = False,
) -> None:
    from cli.commands.stop import cmd_stop
    cmd_stop(volumes=volumes)


@app.command(help="Show real-time status of all services and ZFI score.")
def status(
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Refresh every 5 seconds.")] = False,
) -> None:
    from cli.commands.status import cmd_status
    cmd_status(watch=watch)


@app.command(help="Authenticate with ZANA (OAuth device flow).")
def login(
    reauth: Annotated[bool, typer.Option("--reauth", help="Force re-authentication.")] = False,
) -> None:
    from cli.commands.login import cmd_login, CREDENTIALS_FILE
    if reauth and CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
    cmd_login()


@app.command(help="Remove stored credentials.")
def logout() -> None:
    from cli.commands.login import cmd_logout
    cmd_logout()


@app.command(help="Interactive chat with ZANA via Gateway WebSocket.")
def chat() -> None:
    from cli.commands.chat import cmd_chat
    cmd_chat()


@app.command(help="Embed documents from your vault into ChromaDB.")
def embed(
    vault: Annotated[Optional[str], typer.Argument(help="Path to vault directory.")] = None,
    reset: Annotated[bool, typer.Option("--reset", help="Clear existing embeddings first.")] = False,
) -> None:
    from cli.commands.embed import cmd_embed
    cmd_embed(vault_path=vault, reset=reset)


@app.command(help="Check for and install CLI updates.")
def upgrade(
    check: Annotated[bool, typer.Option("--check", help="Only check, do not install.")] = False,
) -> None:
    from cli.commands.upgrade import cmd_upgrade
    cmd_upgrade(check_only=check)


@app.command(help="Run first-time setup wizard.")
def setup() -> None:
    run_onboarding()


# ── Aeon sub-commands ─────────────────────────────────────────────────────────

@aeon_app.command("list", help="Show all available Aeons and the active one.")
def aeon_list() -> None:
    from cli.commands.aeon import cmd_list
    cmd_list()


@aeon_app.command("use", help="Switch the active Aeon for this session.")
def aeon_use(
    aeon_id: Annotated[str, typer.Argument(help="Aeon ID (e.g. forge, analyst, scholar).")],
) -> None:
    from cli.commands.aeon import cmd_use
    cmd_use(aeon_id)


@aeon_app.command("recommend", help="Let ZANA recommend the best Aeon for a task.")
def aeon_recommend(
    context: Annotated[Optional[str], typer.Argument(help="Describe what you need.")] = None,
) -> None:
    from cli.commands.aeon import cmd_recommend
    cmd_recommend(context)


@aeon_app.command("status", help="Show active Aeon details.")
def aeon_status() -> None:
    from cli.commands.aeon import cmd_status
    cmd_status()


if __name__ == "__main__":
    app()
