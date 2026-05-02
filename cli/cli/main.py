from typing import Annotated, Optional

import typer
from cli.tui.theme import console, BANNER
from cli.tui.onboarding import run_onboarding, run_init_wizard, is_first_run

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

memory_app = typer.Typer(
    name="memory",
    help="Query and inspect ZANA's 4-store memory system.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(memory_app, name="memory")

shadow_app = typer.Typer(
    name="shadow",
    help="Shadow Observer daemon — silent background monitoring.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(shadow_app, name="shadow")

swarm_app = typer.Typer(
    name="swarm",
    help="Red Queen swarm layer — multi-Aeon evolutionary fleet.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(swarm_app, name="swarm")


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
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        console.print(BANNER)
        console.print(
            "[primary]ZANA en línea. Sensores activos. ¿Qué imperio construiremos hoy?[/primary]"
        )
        console.print(
            "\n[muted]Run [accent]zana --help[/accent] to see available commands.[/muted]"
        )


@app.command(help="Boot the full ZANA stack (Docker services).")
def start(
    no_detach: Annotated[
        bool, typer.Option("--no-detach", help="Run in foreground.")
    ] = False,
) -> None:
    if is_first_run():
        run_onboarding()

    from cli.commands.start import cmd_start

    cmd_start(detach=not no_detach)


@app.command(help="Stop all ZANA services.")
def stop(
    volumes: Annotated[
        bool, typer.Option("--volumes", "-v", help="Also remove Docker volumes.")
    ] = False,
) -> None:
    from cli.commands.stop import cmd_stop

    cmd_stop(volumes=volumes)


@app.command(help="Show real-time status of all services and ZFI score.")
def status(
    watch: Annotated[
        bool, typer.Option("--watch", "-w", help="Refresh every 5 seconds.")
    ] = False,
) -> None:
    from cli.commands.status import cmd_status

    cmd_status(watch=watch)


@app.command(help="Authenticate with ZANA (OAuth device flow).")
def login(
    reauth: Annotated[
        bool, typer.Option("--reauth", help="Force re-authentication.")
    ] = False,
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
    vault: Annotated[
        Optional[str], typer.Argument(help="Path to vault directory.")
    ] = None,
    reset: Annotated[
        bool, typer.Option("--reset", help="Clear existing embeddings first.")
    ] = False,
) -> None:
    from cli.commands.embed import cmd_embed

    cmd_embed(vault_path=vault, reset=reset)


@app.command(help="Check for and install CLI updates.")
def upgrade(
    check: Annotated[
        bool, typer.Option("--check", help="Only check, do not install.")
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option("--no-interactive", help="Install without confirmation."),
    ] = False,
) -> None:
    from cli.commands.upgrade import cmd_upgrade

    cmd_upgrade(check_only=check, no_interactive=no_interactive)


@app.command(help="Run first-time setup wizard.")
def setup() -> None:
    run_onboarding()


@app.command(help="Zero-friction Aeon initialization — ≤5 questions, <3 min to first conversation.")
def init() -> None:
    run_init_wizard()


@app.command(help="Full system health audit — environment, services, config.")
def doctor() -> None:
    from cli.commands.doctor import cmd_doctor

    cmd_doctor()


@app.command(help="Expose Aria UI securely to the public internet via Cloudflare Tunnels.")
def expose(
    port: Annotated[
        int, typer.Option("--port", "-p", help="Local port to expose (default 54448 for Aria UI).")
    ] = 54448,
) -> None:
    from cli.commands.expose import cmd_expose

    cmd_expose(port=port)


@app.command(
    name="hardware",
    help=(
        "Analyze your hardware and get LLM recommendations via llmfit. "
        "llmfit scores ~106 models by quality, speed, and fit for your exact CPU/GPU/RAM — "
        "so you know which model to pull before running out of memory."
    ),
)
def hardware(
    install: Annotated[
        bool,
        typer.Option("--install", help="Install llmfit automatically if not present."),
    ] = False,
    recommend: Annotated[
        bool,
        typer.Option("--recommend", "-r", help="Show model recommendations for your hardware."),
    ] = False,
    top: Annotated[
        int,
        typer.Option("--top", "-n", help="Number of models to show."),
    ] = 5,
) -> None:
    from cli.commands.hardware import cmd_hardware

    cmd_hardware(install=install, recommend=recommend, top=top)


@app.command(help="Trigger manual forward-chaining in the Rust reasoning engine.")
def reason(
    fact: Annotated[
        str,
        typer.Argument(help="Fact as JSON or key=value. E.g. machine_health_avg=0.3"),
    ],
    remote: Annotated[
        bool,
        typer.Option(
            "--remote",
            "-r",
            help="Also query the swarm if local rules are insufficient.",
        ),
    ] = False,
) -> None:
    from cli.commands.reason import cmd_reason

    cmd_reason(fact, remote=remote)


project_app = typer.Typer(
    name="project",
    help="Manage isolated cognitive contexts for different projects.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(project_app, name="project")

id_app = typer.Typer(
    name="id",
    help="Manage your cryptographically signed Sovereign ZANA Identity.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(id_app, name="id")

@id_app.command("generate", help="Forge a new Sovereign ZANA Identity.")
def id_generate(
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite existing identity.")
    ] = False,
) -> None:
    from cli.commands.identity import cmd_id_generate
    cmd_id_generate(force=force)

@id_app.command("show", help="Display your public ZANA ID.")
def id_show() -> None:
    from cli.commands.identity import cmd_id_show
    cmd_id_show()

# ── Aeon sub-commands ─────────────────────────────────────────────────────────


@aeon_app.command("list", help="Show all available Aeons and the active one.")
def aeon_list() -> None:
    from cli.commands.aeon import cmd_list

    cmd_list()


@aeon_app.command("use", help="Switch the active Aeon for this session.")
def aeon_use(
    aeon_id: Annotated[
        str, typer.Argument(help="Aeon ID (e.g. forge, analyst, scholar).")
    ],
) -> None:
    from cli.commands.aeon import cmd_use

    cmd_use(aeon_id)


@aeon_app.command("recommend", help="Let ZANA recommend the best Aeon for a task.")
def aeon_recommend(
    context: Annotated[
        Optional[str], typer.Argument(help="Describe what you need.")
    ] = None,
) -> None:
    from cli.commands.aeon import cmd_recommend

    cmd_recommend(context)


@aeon_app.command("status", help="Show active Aeon details.")
def aeon_status() -> None:
    from cli.commands.aeon import cmd_status

    cmd_status()


# ── Memory sub-commands ───────────────────────────────────────────────────────


@memory_app.command("search", help="Semantic search in ChromaDB vault.")
def memory_search(
    query: Annotated[str, typer.Argument(help="Natural language query.")],
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="ChromaDB collection name.")
    ] = "zana_vault",
    n: Annotated[int, typer.Option("--top", "-n", help="Number of results.")] = 5,
) -> None:
    from cli.commands.memory import cmd_memory_search

    cmd_memory_search(query, collection=collection, n=n)


@memory_app.command("recall", help="Last N episodic memories from PostgreSQL.")
def memory_recall(
    n: Annotated[int, typer.Argument(help="Number of records to retrieve.")] = 10,
) -> None:
    from cli.commands.memory import cmd_memory_recall

    cmd_memory_recall(n)


@memory_app.command("stats", help="Collection sizes across all 4 memory stores.")
def memory_stats() -> None:
    from cli.commands.memory import cmd_memory_stats

    cmd_memory_stats()


# ── Shadow sub-commands ───────────────────────────────────────────────────────


@shadow_app.command("enable", help="Start the Shadow Observer daemon.")
def shadow_enable() -> None:
    from cli.commands.shadow import cmd_shadow_enable

    cmd_shadow_enable()


@shadow_app.command("disable", help="Stop the Shadow Observer daemon.")
def shadow_disable() -> None:
    from cli.commands.shadow import cmd_shadow_disable

    cmd_shadow_disable()


@shadow_app.command("status", help="Show Shadow Observer daemon health.")
def shadow_status() -> None:
    from cli.commands.shadow import cmd_shadow_status

    cmd_shadow_status()


# ── Swarm sub-commands (v2.2) ─────────────────────────────────────────────────


@swarm_app.command(
    "init", help="Bootstrap Red Queen — spawn and evolve the warrior fleet."
)
def swarm_init(
    warriors: Annotated[
        int, typer.Option("--warriors", "-w", help="Number of warriors to spawn.")
    ] = 50,
    generations: Annotated[
        int, typer.Option("--generations", "-g", help="Evolution generations.")
    ] = 2000,
) -> None:
    from cli.commands.swarm import cmd_swarm_init

    cmd_swarm_init(warriors=warriors, generations=generations)


@swarm_app.command("status", help="Live warrior fleet dashboard.")
def swarm_status(
    watch: Annotated[
        bool, typer.Option("--watch", "-w", help="Auto-refresh every 3 seconds.")
    ] = False,
) -> None:
    from cli.commands.swarm import cmd_swarm_status

    cmd_swarm_status(watch=watch)


@swarm_app.command("stop", help="Stop all swarm warriors.")
def swarm_stop() -> None:
    from cli.commands.swarm import cmd_swarm_stop

    cmd_swarm_stop()


@swarm_app.command("sync", help="Pull validated WisdomRules from the Wisdom Hub.")
def swarm_sync() -> None:
    from cli.commands.swarm import cmd_swarm_sync

    cmd_swarm_sync()


@swarm_app.command("query", help="Ask the swarm for rules covering a given fact.")
def swarm_query(
    fact_key: Annotated[
        str, typer.Argument(help="Fact key to query (e.g. machine_health_avg).")
    ],
) -> None:
    from cli.commands.swarm import cmd_swarm_query

    cmd_swarm_query(fact_key)


from cli.commands.sync import app as sync_app
app.add_typer(sync_app, name="sync")

wisdom_app = typer.Typer(
    name="wisdom",
    help="Auto-WisdomRules inbox — review, approve, and mine skills from sessions.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(wisdom_app, name="wisdom")


@wisdom_app.command("inbox", help="List pending wisdom proposals.")
def wisdom_inbox() -> None:
    from cli.commands.wisdom import cmd_wisdom_inbox
    cmd_wisdom_inbox()


@wisdom_app.command("mine", help="Trigger trajectory mining to generate new proposals.")
def wisdom_mine() -> None:
    from cli.commands.wisdom import cmd_wisdom_mine
    cmd_wisdom_mine()


@wisdom_app.command("approve", help="Approve a proposal and register it as an active skill.")
def wisdom_approve(
    wisdom_id: Annotated[str, typer.Argument(help="Wisdom proposal ID.")],
) -> None:
    from cli.commands.wisdom import cmd_wisdom_approve
    cmd_wisdom_approve(wisdom_id)


@wisdom_app.command("reject", help="Reject a wisdom proposal.")
def wisdom_reject(
    wisdom_id: Annotated[str, typer.Argument(help="Wisdom proposal ID.")],
) -> None:
    from cli.commands.wisdom import cmd_wisdom_reject
    cmd_wisdom_reject(wisdom_id)

if __name__ == "__main__":
    app()
