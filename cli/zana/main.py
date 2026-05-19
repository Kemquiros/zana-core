from pathlib import Path
from typing import Annotated

import typer

from zana.tui.onboarding import is_first_run, run_init_wizard, run_onboarding
from zana.tui.theme import BANNER, console

app = typer.Typer(
    name="zana",
    help="ZANA — Zero Autonomous Neural Architecture · Works offline · No Docker required",
    no_args_is_help=False,
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

coliseum_app = typer.Typer(
    name="coliseum",
    help="AEON MULTIVERSE — The First Artificial Life Coliseum.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
from zana.commands.coliseum import app as coliseum_typer  # noqa: E402

coliseum_app.add_typer(coliseum_typer, name="")
app.add_typer(coliseum_app, name="coliseum")


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version

        try:
            v = version("vecanova-zana")
        except Exception:
            v = "3.2.0"
        console.print(f"[primary]ZANA[/primary] [muted]v{v}[/muted]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    if ctx.invoked_subcommand:
        import time as _time

        from zana.sentinel_hooks import fire_post_tool_use, fire_pre_tool_use

        _t0 = _time.perf_counter()
        fire_pre_tool_use(ctx.invoked_subcommand)

        def _on_close():
            fire_post_tool_use(
                ctx.invoked_subcommand,
                success=True,
                elapsed_ms=(_time.perf_counter() - _t0) * 1000,
            )

        ctx.call_on_close(_on_close)
        return

    console.print(BANNER)
    try:
        import os as _os

        from zana.core.tier import detect_tier as _dt
        from zana.core.tier import tier_label as _tl
        from zana.core.tier import tier_next_action as _tna
        from zana.core.tier import tier_progress_bar as _tpb
        from zana.core.zsm import load_env_file as _lef
        from zana.tui.aeon_dna import AeonProfile as _AeonProfile

        _lef()
        _tier = _dt()
        _lang = _os.environ.get("ZANA_LANG", "es")
        _profile = _AeonProfile.load()
        _name = _profile.name if _profile else "ZANA"
        _raw_arch = (
            _profile.archetype.value
            if _profile and hasattr(_profile, "archetype")
            else ""
        )
        _arch = _raw_arch.capitalize() if _raw_arch and _raw_arch != "unknown" else ""
        _bar = _tpb(_tier)
        _label = _tl(_tier, _lang)
        _action = _tna(_tier, _lang)
        _arch_str = f" · {_arch}" if _arch else ""
        console.print(
            f"[primary]{_name}[/primary]{_arch_str}  [muted][{_bar}] {_label}[/muted]"
        )
        console.print(f"[muted]→ {_action}[/muted]")
        console.print(
            "\n[muted]Run [accent]zana --help[/accent] to see available commands.[/muted]"
        )
        console.print(
            "[muted]Modo Soberano disponible sin Docker — escribe [accent]zana chat[/accent] para comenzar.[/muted]"
        )
    except Exception:
        console.print(
            "[primary]ZANA en línea. Sensores activos. ¿Qué imperio construiremos hoy?[/primary]"
        )
        console.print(
            "\n[muted]Run [accent]zana --help[/accent] to see available commands.[/muted]"
        )
        console.print(
            "[muted]Modo Soberano disponible sin Docker — escribe [accent]zana chat[/accent] para comenzar.[/muted]"
        )


@app.command(help="Boot the full ZANA stack (Docker services).")
def start(
    no_detach: Annotated[
        bool, typer.Option("--no-detach", help="Run in foreground.")
    ] = False,
) -> None:
    if is_first_run():
        run_onboarding()

    from zana.commands.start import cmd_start

    cmd_start(detach=not no_detach)


@app.command(help="Stop all ZANA services.")
def stop(
    volumes: Annotated[
        bool, typer.Option("--volumes", "-v", help="Also remove Docker volumes.")
    ] = False,
) -> None:
    from zana.commands.stop import cmd_stop

    cmd_stop(volumes=volumes)


@app.command(help="Show real-time status of all services and ZFI score.")
def status(
    watch: Annotated[
        bool, typer.Option("--watch", "-w", help="Refresh every 5 seconds.")
    ] = False,
) -> None:
    from zana.commands.status import cmd_status

    cmd_status(watch=watch)


@app.command(help="Authenticate with ZANA (OAuth device flow).")
def login(
    reauth: Annotated[
        bool, typer.Option("--reauth", help="Force re-authentication.")
    ] = False,
) -> None:
    from zana.commands.login import CREDENTIALS_FILE, cmd_login

    if reauth and CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
    cmd_login()


@app.command(help="Remove stored credentials.")
def logout() -> None:
    from zana.commands.login import cmd_logout

    cmd_logout()


@app.command(help="Interactive chat with ZANA via Gateway WebSocket.")
def chat() -> None:
    from zana.commands.chat import cmd_chat

    cmd_chat()


@app.command(help="Embed documents from your vault into ChromaDB.")
def embed(
    vault: Annotated[
        str | None, typer.Argument(help="Path to vault directory.")
    ] = None,
    reset: Annotated[
        bool, typer.Option("--reset", help="Clear existing embeddings first.")
    ] = False,
) -> None:
    from zana.commands.embed import cmd_embed

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
    from zana.commands.upgrade import cmd_upgrade

    cmd_upgrade(check_only=check, no_interactive=no_interactive)


@app.command(help="Run first-time setup wizard.")
def setup() -> None:
    run_onboarding()


@app.command(help="Uninstall ZANA CLI from this system.")
def uninstall(
    purge: Annotated[
        bool,
        typer.Option(
            "--purge",
            help="Complete removal: package + all local data (~/.zana, app dirs).",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    from zana.commands.uninstall import cmd_uninstall

    cmd_uninstall(purge=purge, yes=yes)


@app.command(
    help="Zero-friction Aeon initialization — ≤5 questions, <3 min to first conversation."
)
def init() -> None:
    run_init_wizard()


@app.command(help="Show the single next action to advance to the next tier.")
def next() -> None:
    from zana.commands.next import cmd_next

    cmd_next()


@app.command(help="Full system health audit — environment, services, config.")
def doctor(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Interactively repair detected issues after audit."),
    ] = False,
) -> None:
    from zana.commands.doctor import cmd_doctor

    cmd_doctor(fix=fix)


@app.command(
    help="Expose Aria UI securely to the public internet via Cloudflare Tunnels."
)
def expose(
    port: Annotated[
        int,
        typer.Option(
            "--port", "-p", help="Local port to expose (default 54448 for Aria UI)."
        ),
    ] = 54448,
) -> None:
    from zana.commands.expose import cmd_expose

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
        typer.Option(
            "--recommend", "-r", help="Show model recommendations for your hardware."
        ),
    ] = False,
    top: Annotated[
        int,
        typer.Option("--top", "-n", help="Number of models to show."),
    ] = 5,
) -> None:
    from zana.commands.hardware import cmd_hardware

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
    from zana.commands.reason import cmd_reason

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
    from zana.commands.identity import cmd_id_generate

    cmd_id_generate(force=force)


@id_app.command("show", help="Display your public ZANA ID.")
def id_show() -> None:
    from zana.commands.identity import cmd_id_show

    cmd_id_show()


# ── Aeon sub-commands ─────────────────────────────────────────────────────────


@aeon_app.command("list", help="Show all available Aeons and the active one.")
def aeon_list() -> None:
    from zana.commands.aeon import cmd_list

    cmd_list()


@aeon_app.command("use", help="Switch the active Aeon for this session.")
def aeon_use(
    aeon_id: Annotated[
        str, typer.Argument(help="Aeon ID (e.g. forge, analyst, scholar).")
    ],
) -> None:
    from zana.commands.aeon import cmd_use

    cmd_use(aeon_id)


@aeon_app.command("recommend", help="Let ZANA recommend the best Aeon for a task.")
def aeon_recommend(
    context: Annotated[
        str | None, typer.Argument(help="Describe what you need.")
    ] = None,
) -> None:
    from zana.commands.aeon import cmd_recommend

    cmd_recommend(context)


@aeon_app.command("status", help="Show active Aeon details.")
def aeon_status() -> None:
    from zana.commands.aeon import cmd_status

    cmd_status()


@aeon_app.command("export", help="Export your Aeon DNA to a .aeon file.")
def aeon_export(
    path: Annotated[Path | None, typer.Argument(help="Output path.")] = None,
) -> None:
    from zana.commands.aeon import cmd_export

    cmd_export(path)


@aeon_app.command("summon", help="Summon an external Aeon from a .aeon file.")
def aeon_summon(
    path: Annotated[Path, typer.Argument(help="Path to .aeon file.")],
) -> None:
    from zana.commands.aeon import cmd_summon

    cmd_summon(path)


@aeon_app.command("sigil", help="Animated Aeon sigil — living visual representation.")
def aeon_sigil(
    duration: Annotated[
        float,
        typer.Option(
            "--duration", "-d", help="Seconds to animate (0 = loop until Ctrl+C)."
        ),
    ] = 0,
) -> None:
    from zana.commands.aeon import cmd_sigil

    cmd_sigil(duration=duration or None)


@aeon_app.command("card", help="Show and export your Aeon Card (shareable).")
def aeon_card(
    export: Annotated[
        bool, typer.Option("--export", help="Save card to ~/.zana/aeon_card.txt")
    ] = False,
) -> None:
    from zana.commands.aeon import cmd_card

    cmd_card(export=export)


@aeon_app.command(
    "resonance", help="Run the Resonance Test to calibrate your Aeon archetype."
)
def aeon_resonance() -> None:
    from zana.commands.aeon import cmd_resonance

    cmd_resonance()


@aeon_app.command(
    "habitat", help="Your Aeon in its 2.5D world — living environment animation."
)
def aeon_habitat(
    fps: Annotated[
        int, typer.Option("--fps", help="Animation frames per second (default 4).")
    ] = 4,
) -> None:
    from zana.commands.aeon import cmd_habitat

    cmd_habitat(fps=fps)


@aeon_app.command("dna", help="Show your Aeon's full 21-gene DNA vector.")
def aeon_dna() -> None:
    from zana.commands.aeon import cmd_dna

    cmd_dna()


@aeon_app.command("tune", help="Interactively tune your Aeon's DNA genes.")
def aeon_tune(
    gene: Annotated[
        str | None,
        typer.Argument(
            help="Gene name or number to tune (e.g. curiosity, g9, 9). Omit for full interactive mode."
        ),
    ] = None,
) -> None:
    from zana.commands.aeon import cmd_tune

    cmd_tune(gene=gene)


# ── Memory sub-commands ───────────────────────────────────────────────────────


@memory_app.command(
    "add", help="Add a document to local SQLite FTS5 memory (no Docker required)."
)
def memory_add(
    text: Annotated[str, typer.Argument(help="Text to store in memory.")],
    source: Annotated[
        str, typer.Option("--source", "-s", help="Source label.")
    ] = "cli",
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="Collection name.")
    ] = "zana_vault",
    tag: Annotated[
        str | None, typer.Option("--tag", "-t", help="Optional tag.")
    ] = None,
) -> None:
    from zana.commands.memory import cmd_memory_add

    cmd_memory_add(text, source=source, collection=collection, tag=tag)


@memory_app.command("search", help="Semantic search in ChromaDB vault.")
def memory_search(
    query: Annotated[str, typer.Argument(help="Natural language query.")],
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="ChromaDB collection name.")
    ] = "zana_vault",
    n: Annotated[int, typer.Option("--top", "-n", help="Number of results.")] = 5,
) -> None:
    from zana.commands.memory import cmd_memory_search

    cmd_memory_search(query, collection=collection, n=n)


@memory_app.command("recall", help="Last N episodic memories from PostgreSQL.")
def memory_recall(
    n: Annotated[int, typer.Argument(help="Number of records to retrieve.")] = 10,
) -> None:
    from zana.commands.memory import cmd_memory_recall

    cmd_memory_recall(n)


@memory_app.command("stats", help="Collection sizes across all 4 memory stores.")
def memory_stats() -> None:
    from zana.commands.memory import cmd_memory_stats

    cmd_memory_stats()


@memory_app.command("delete", help="Delete a document by ID from local SQLite memory.")
def memory_delete(
    doc_id: int = typer.Argument(
        ..., help="Document ID to delete (see: zana memory search)"
    ),
) -> None:
    from zana.commands.memory import cmd_memory_delete

    cmd_memory_delete(doc_id)


@memory_app.command(
    "clear", help="Delete all documents — optionally from one collection only."
)
def memory_clear(
    collection: str | None = typer.Option(
        None, "--collection", "-c", help="Collection to clear (omit = all)."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    from zana.commands.memory import cmd_memory_clear

    if not yes:
        target = f"'{collection}'" if collection else "ALL collections"
        confirm = typer.confirm(f"Delete all documents from {target}?", default=False)
        if not confirm:
            raise typer.Abort()
    cmd_memory_clear(collection=collection)


@memory_app.command("export", help="Export SQLite FTS5 memory to JSON or CSV.")
def memory_export(
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)."
    ),
    collection: str | None = typer.Option(
        None, "--collection", "-c", help="Export only this collection."
    ),
    fmt: str = typer.Option(
        "json", "--format", "-f", help="Output format: json or csv."
    ),
) -> None:
    from zana.commands.memory import cmd_memory_export

    cmd_memory_export(collection=collection, fmt=fmt, output=output)


@memory_app.command(
    "import", help="Import documents from a JSON file into SQLite FTS5 memory."
)
def memory_import(
    path: str = typer.Argument(
        ..., help="Path to the JSON file exported by 'zana memory export'."
    ),
) -> None:
    from zana.commands.memory import cmd_memory_import

    cmd_memory_import(path)


# ── Shadow sub-commands ───────────────────────────────────────────────────────


@shadow_app.command("enable", help="Start the Shadow Observer daemon.")
def shadow_enable() -> None:
    from zana.commands.shadow import cmd_shadow_enable

    cmd_shadow_enable()


@shadow_app.command("disable", help="Stop the Shadow Observer daemon.")
def shadow_disable() -> None:
    from zana.commands.shadow import cmd_shadow_disable

    cmd_shadow_disable()


@shadow_app.command("status", help="Show Shadow Observer daemon health.")
def shadow_status() -> None:
    from zana.commands.shadow import cmd_shadow_status

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
    from zana.commands.swarm import cmd_swarm_init

    cmd_swarm_init(warriors=warriors, generations=generations)


@swarm_app.command("status", help="Live warrior fleet dashboard.")
def swarm_status(
    watch: Annotated[
        bool, typer.Option("--watch", "-w", help="Auto-refresh every 3 seconds.")
    ] = False,
) -> None:
    from zana.commands.swarm import cmd_swarm_status

    cmd_swarm_status(watch=watch)


@swarm_app.command("stop", help="Stop all swarm warriors.")
def swarm_stop() -> None:
    from zana.commands.swarm import cmd_swarm_stop

    cmd_swarm_stop()


@swarm_app.command("sync", help="Pull validated WisdomRules from the Wisdom Hub.")
def swarm_sync() -> None:
    from zana.commands.swarm import cmd_swarm_sync

    cmd_swarm_sync()


@swarm_app.command("query", help="Ask the swarm for rules covering a given fact.")
def swarm_query(
    fact_key: Annotated[
        str, typer.Argument(help="Fact key to query (e.g. machine_health_avg).")
    ],
) -> None:
    from zana.commands.swarm import cmd_swarm_query

    cmd_swarm_query(fact_key)


from zana.commands.sync import app as sync_app  # noqa: E402

app.add_typer(sync_app, name="sync")

world_app = typer.Typer(
    name="world",
    help="ZANA — World Layer interface for artifact management.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
from zana.commands.world import app as world_typer  # noqa: E402

world_app.add_typer(world_typer, name="")
app.add_typer(world_app, name="world")

satellite_app = typer.Typer(
    name="satellite",
    help="Satellite connectivity layer — Telegram, Discord.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
from zana.commands.satellite import app as satellite_typer  # noqa: E402

satellite_app.add_typer(satellite_typer, name="")
app.add_typer(satellite_app, name="satellite")

sentinel_app = typer.Typer(
    name="sentinel",
    help="Sentinel Event Bus — lifecycle events and Civic Ledger audit.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(sentinel_app, name="sentinel")


@sentinel_app.command("status", help="Bus health + event type counts.")
def sentinel_status() -> None:
    from zana.commands.sentinel import cmd_sentinel_status

    cmd_sentinel_status()


@sentinel_app.command("events", help="Recent events from the in-memory ring buffer.")
def sentinel_events(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of events.")] = 20,
    event_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by event type.")
    ] = None,
) -> None:
    from zana.commands.sentinel import cmd_sentinel_events

    cmd_sentinel_events(limit=limit, event_type=event_type)


@sentinel_app.command(
    "ledger",
    help="Read recent entries from the Civic Ledger (~/.zana/civic_ledger.jsonl).",
)
def sentinel_ledger(
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Number of entries.")
    ] = 20,
) -> None:
    from zana.commands.sentinel import cmd_sentinel_ledger

    cmd_sentinel_ledger(limit=limit)


wisdom_app = typer.Typer(
    name="wisdom",
    help="Auto-WisdomRules inbox — review, approve, and mine skills from sessions.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(wisdom_app, name="wisdom")


@wisdom_app.command("inbox", help="List pending wisdom proposals.")
def wisdom_inbox() -> None:
    from zana.commands.wisdom import cmd_wisdom_inbox

    cmd_wisdom_inbox()


@wisdom_app.command("mine", help="Trigger trajectory mining to generate new proposals.")
def wisdom_mine() -> None:
    from zana.commands.wisdom import cmd_wisdom_mine

    cmd_wisdom_mine()


@wisdom_app.command(
    "approve", help="Approve a proposal and register it as an active skill."
)
def wisdom_approve(
    wisdom_id: Annotated[str, typer.Argument(help="Wisdom proposal ID.")],
) -> None:
    from zana.commands.wisdom import cmd_wisdom_approve

    cmd_wisdom_approve(wisdom_id)


@wisdom_app.command("reject", help="Reject a wisdom proposal.")
def wisdom_reject(
    wisdom_id: Annotated[str, typer.Argument(help="Wisdom proposal ID.")],
) -> None:
    from zana.commands.wisdom import cmd_wisdom_reject

    cmd_wisdom_reject(wisdom_id)


# ── MCP sub-commands ──────────────────────────────────────────────────────────

mcp_app = typer.Typer(
    name="mcp",
    help="Model Context Protocol server — connect Claude Code, Cline, and other MCP clients to ZANA memory.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("start", help="Start the ZANA MCP memory server (stdio or SSE).")
def mcp_start(
    port: Annotated[
        int | None,
        typer.Option(
            "--port", "-p", help="Run SSE transport on this port (omit for stdio)."
        ),
    ] = None,
    background: Annotated[
        bool, typer.Option("--background", "-b", help="Run as background daemon.")
    ] = False,
) -> None:
    import os
    import subprocess
    from pathlib import Path

    server = Path(__file__).parent.parent.parent / "mcp" / "zana-memory" / "server.py"
    if not server.exists():
        console.print(f"[error]MCP server not found at {server}[/error]")
        raise typer.Exit(1)

    env = os.environ.copy()
    if port:
        env["ZANA_MCP_PORT"] = str(port)

    console.print(
        f"\n[primary]ZANA MCP[/primary] [muted]{'SSE :' + str(port) if port else 'stdio'}[/muted]\n"
        f"[muted]Server:[/muted] {server}\n"
        f"[muted]Backend:[/muted] SQLite FTS5 (SPROUT) → Rust vector index (GROVE+)\n"
    )

    if background:
        import sys

        proc = subprocess.Popen(
            [sys.executable, str(server)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print(f"[success]✓ MCP server started (PID {proc.pid})[/success]")
        config_hint = (
            f'{{"zana": {{"command": "{sys.executable}", "args": ["{server}"]}}}}'
        )
        console.print(
            "[muted]Add to claude_desktop_config.json:[/muted]\n"
            f"  [accent]{config_hint}[/accent]"
        )
    else:
        subprocess.run(
            [__import__("sys").executable, str(server)], env=env, check=False
        )


@mcp_app.command(
    "config",
    help="Print the MCP config block to paste into claude_desktop_config.json.",
)
def mcp_config() -> None:
    import json
    import sys
    from pathlib import Path

    server = Path(__file__).parent.parent.parent / "mcp" / "zana-memory" / "server.py"
    block = {"zana": {"command": sys.executable, "args": [str(server)]}}
    console.print(
        "\n[primary]MCP Config[/primary] [muted]— paste into claude_desktop_config.json[/muted]\n"
    )
    console.print(json.dumps(block, indent=2))
    console.print(
        "\n[muted]Config file location:[/muted]\n"
        "  macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json\n"
        "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json\n"
        "  Linux:   ~/.config/Claude/claude_desktop_config.json\n"
    )


if __name__ == "__main__":
    app()
