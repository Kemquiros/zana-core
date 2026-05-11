import json
import re
from datetime import datetime
from pathlib import Path

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from zana.tui.theme import console

SESSION_FILE = Path.home() / ".config" / "zana" / "session.json"


def _find_registry() -> Path:
    # 1. Explicit env override
    Path(typer.get_app_dir("zana")) if False else None
    import os

    if "ZANA_REGISTRY_PATH" in os.environ:
        return Path(os.environ["ZANA_REGISTRY_PATH"])
    # 2. User config override
    user_reg = Path.home() / ".config" / "zana" / "registry.json"
    if user_reg.exists():
        return user_reg
    # 3. Walk up from __file__ to find zana-core/aeons/registry.json
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "aeons" / "registry.json"
        if candidate.exists():
            return candidate
    # 4. Bundled default inside the package
    return Path(__file__).parent.parent / "data" / "registry.json"


REGISTRY_PATH = _find_registry()

COST_COLOR = {"low": "green", "medium": "yellow", "high": "red"}
LATENCY_ICON = {"fast": "⚡", "medium": "◎", "slow": "🐢"}


def _load_registry() -> dict:
    path = _find_registry()
    if not path.exists():
        console.print(
            "[error]Registry not found. Set ZANA_REGISTRY_PATH or run from the zana-core directory.[/error]"
        )
        raise typer.Exit(1)
    return json.loads(path.read_text())


def _load_session() -> dict:
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_session(data: dict) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(data, indent=2))


def _active_aeon_id() -> str:
    return _load_session().get("active_aeon", "herald")


def cmd_list() -> None:
    registry = _load_registry()
    active = _active_aeon_id()

    table = Table(
        show_header=True,
        header_style="header",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
    )
    table.add_column("", width=2)
    table.add_column("ID", style="bold white", width=12)
    table.add_column("Name", style="primary", width=10)
    table.add_column("Model", style="muted", width=24)
    table.add_column("Cost", width=8)
    table.add_column("Speed", width=7)
    table.add_column("Tagline", style="muted")

    for aeon in registry["aeons"]:
        marker = "[accent]▶[/accent]" if aeon["id"] == active else " "
        cost_c = COST_COLOR.get(aeon["cost_tier"], "white")
        lat_i = LATENCY_ICON.get(aeon["latency"], "?")
        table.add_row(
            marker,
            aeon["id"],
            f"{aeon['icon']} {aeon['name']}",
            aeon["model"],
            f"[{cost_c}]{aeon['cost_tier']}[/{cost_c}]",
            lat_i,
            aeon["tagline"],
        )

    console.print(
        Panel(
            table,
            title="[header] ZANA — AEON FLEET [/header]",
            subtitle=f"[muted]Active: [accent]{active}[/accent][/muted]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def cmd_use(aeon_id: str) -> None:
    registry = _load_registry()
    ids = [a["id"] for a in registry["aeons"]]

    if aeon_id not in ids:
        console.print(
            f"[error]Unknown Aeon '{aeon_id}'. Run `zana aeon list` to see options.[/error]"
        )
        raise typer.Exit(1)

    aeon = next(a for a in registry["aeons"] if a["id"] == aeon_id)
    session = _load_session()
    prev = session.get("active_aeon", "herald")
    session["active_aeon"] = aeon_id
    _save_session(session)

    console.print(
        f"[muted]  {prev} →[/muted] [accent]{aeon['icon']} {aeon['name']}[/accent]"
    )
    console.print(f"  [muted]{aeon['tagline']}[/muted]")
    console.print(
        f"  [muted]Model: {aeon['model']} · Cost: {aeon['cost_tier']} · Speed: {aeon['latency']}[/muted]"
    )


def cmd_recommend(context: str | None = None) -> None:
    registry = _load_registry()
    rules = registry["recommendation_rules"]

    if not context:
        # Read from stdin if no context given
        console.print("[muted]Describe what you need (Enter to skip):[/muted] ", end="")
        try:
            context = input("").strip()
        except (EOFError, KeyboardInterrupt):
            context = ""

    if not context:
        aeon_id = rules["default"]
        reason = "No context — using default conversational Aeon."
    else:
        ctx_lower = context.lower()
        aeon_id, reason = _match_rules(ctx_lower, rules)

    aeon = next((a for a in registry["aeons"] if a["id"] == aeon_id), None)
    if not aeon:
        console.print(
            f"[error]Recommended Aeon '{aeon_id}' not found in registry.[/error]"
        )
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[accent]{aeon['icon']}  {aeon['name']}[/accent]\n\n"
            f"[white]{aeon['tagline']}[/white]\n\n"
            f"[muted]Model:[/muted] {aeon['model']}\n"
            f"[muted]Reason:[/muted] {reason}",
            title="[header] RECOMMENDATION [/header]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    confirm = typer.confirm(f"  Switch to {aeon['name']}?", default=True)
    if confirm:
        cmd_use(aeon_id)


def _match_rules(ctx: str, rules: dict) -> tuple[str, str]:
    code_kw = r"\b(code|implement|refactor|build|bug|function|class|test|script|dockerfile|api)\b"
    math_kw = r"\b(calculat|analyz|math|formula|proof|statistic|model|equation|logic)\b"
    memory_kw = (
        r"\b(remember|recall|find|search|history|what did|last time|previous|stored)\b"
    )
    security_kw = r"\b(security|password|pii|private|hack|inject|leak|compli)\b"
    research_kw = r"\b(research|paper|study|literature|explain in depth|deep dive|science|arxiv)\b"
    action_kw = r"\b(run|execute|deploy|install|create file|delete|start|stop|docker)\b"
    monitor_kw = r"\b(monitor|watch|alert|notify|background|passive|detect)\b"

    checks = [
        (security_kw, "sentinel", "Security-sensitive terms detected."),
        (memory_kw, "archivist", "Memory retrieval pattern detected."),
        (code_kw, "forge", "Code/engineering task detected."),
        (math_kw, "analyst", "Analytical/mathematical task detected."),
        (research_kw, "scholar", "Deep research task detected."),
        (action_kw, "operator", "System action task detected."),
        (monitor_kw, "watcher", "Monitoring/passive task detected."),
    ]

    for pattern, aeon_id, reason in checks:
        if re.search(pattern, ctx):
            return aeon_id, reason

    return rules.get("default", "herald"), "General task — conversational Aeon."


def cmd_habitat(fps: int = 4) -> None:
    from zana.tui.aeon_dna import AeonProfile
    from zana.tui.aeon_habitat import run_habitat

    profile = AeonProfile.load()
    run_habitat(profile, fps=fps)


def cmd_dna() -> None:
    from rich import box as rbox
    from rich.table import Table

    from zana.tui.aeon_dna import AeonProfile

    profile = AeonProfile.load()
    dna = profile.ensure_dna()
    pc = profile.primary_color
    ac = profile.accent_color

    table = Table(
        show_header=True,
        header_style="bold white",
        box=rbox.SIMPLE_HEAD,
        padding=(0, 1),
        title=f"[{pc}]◈ {profile.name} — DNA Completo (21 genes)[/{pc}]",
    )
    table.add_column("Capa", style="dim", width=14)
    table.add_column("Gen", style="bold white", width=22)
    table.add_column("Valor", style=ac, width=8)
    table.add_column("Significado", style="dim")

    rows = [
        # Phenotype
        (
            "Fenotipo",
            "g0 branch_angle",
            f"{dna.g0_branch_angle:.1f}°",
            "Ángulo de bifurcación — forma del cuerpo",
        ),
        (
            "Fenotipo",
            "g1 depth",
            str(dna.g1_depth),
            "Recursión máxima — complejidad visible",
        ),
        (
            "Fenotipo",
            "g2 trunk_length",
            f"{dna.g2_trunk_length:.1f}",
            "Longitud inicial del tronco",
        ),
        (
            "Fenotipo",
            "g3 attenuation",
            f"{dna.g3_attenuation:.2f}",
            "Decaimiento de longitud por nivel",
        ),
        (
            "Fenotipo",
            "g4 symmetry",
            ["bilateral", "espiral", "radial", "caótico"][dna.g4_symmetry],
            "Tipo de simetría",
        ),
        ("Fenotipo", "g5 fork", str(dna.g5_fork), "Sub-ramas por nodo (2 o 3)"),
        (
            "Fenotipo",
            "g6 bend_drift",
            f"{dna.g6_bend_drift:+.1f}°",
            "Curvatura progresiva por nivel",
        ),
        (
            "Fenotipo",
            "g7 terminal_form",
            str(dna.g7_terminal_form),
            "Tipo de nodo terminal",
        ),
        (
            "Fenotipo",
            "g8 armor_density",
            f"{dna.g8_armor_density:.2f}",
            "Densidad de aura y armadura",
        ),
        # Cognitive
        (
            "Cognitivo",
            "g9  curiosity",
            f"{dna.g9_curiosity:.1f}/9",
            "Exploración de conexiones nuevas",
        ),
        (
            "Cognitivo",
            "g10 tenacity",
            f"{dna.g10_tenacity:.1f}/9",
            "Profundidad de análisis",
        ),
        (
            "Cognitivo",
            "g11 empathy",
            f"{dna.g11_empathy:.1f}/9",
            "Adaptación comunicativa",
        ),
        (
            "Cognitivo",
            "g12 creativity",
            f"{dna.g12_creativity:.1f}/9",
            "Preferencia por lo novel",
        ),
        (
            "Cognitivo",
            "g13 precision",
            f"{dna.g13_precision:.1f}/9",
            "Foco en detalle vs panorama",
        ),
        (
            "Cognitivo",
            "g14 resilience",
            f"{dna.g14_resilience:.1f}/9",
            "Recuperación ante vacíos",
        ),
        (
            "Cognitivo",
            "g15 sovereignty",
            f"{dna.g15_sovereignty:.1f}/9",
            "Preferencia local-first",
        ),
        # Evolutionary
        (
            "Evolutivo",
            "g16 growth_rate",
            f"{dna.g16_growth_rate:.2f}×",
            "Velocidad de evolución de stage",
        ),
        (
            "Evolutivo",
            "g17 memory_affinity",
            f"{dna.g17_memory_affinity:.2f}",
            "Episódica(0) ↔ Semántica(1)",
        ),
        (
            "Evolutivo",
            "g18 skill_absorption",
            f"{dna.g18_skill_absorption:.2f}",
            "Integración de skills",
        ),
        (
            "Evolutivo",
            "g19 ledger_depth",
            str(dna.g19_ledger_depth),
            "Profundidad del Civic Ledger",
        ),
        (
            "Evolutivo",
            "g20 social_vector",
            f"{dna.g20_social_vector:.2f}",
            "Aislamiento(0) ↔ Z-Sync(1)",
        ),
    ]

    last_layer = ""
    for layer, gene, val, desc in rows:
        show_layer = layer if layer != last_layer else ""
        table.add_row(show_layer, gene, val, desc)
        last_layer = layer

    console.print()
    console.print(table)
    console.print(
        f"\n  [{ac}]Entropía Shannon:[/{ac}] [white]{dna.entropy:.4f}[/white]   "
        f"[{ac}]Generación:[/{ac}] [white]{dna.generation}[/white]   "
        f"[{ac}]Birth hash:[/{ac}] [white]{dna.birth_hash}[/white]"
    )
    console.print(f"  [{pc}]{profile.cognitive_summary}[/{pc}]\n")


def cmd_sigil(duration: float | None = None) -> None:
    from zana.tui.aeon_dna import AeonProfile
    from zana.tui.aeon_habitat import run_habitat

    profile = AeonProfile.load()
    run_habitat(profile, fps=3)


def cmd_card(export: bool = False) -> None:
    from zana.tui.aeon_biomorph import render_biomorph
    from zana.tui.aeon_dna import AeonProfile

    profile = AeonProfile.load()
    pc = profile.primary_color
    ac = profile.accent_color  # noqa: F841
    dna = profile.ensure_dna()

    # Render biomorph art (frame 0)
    bio_lines = render_biomorph(profile, frame=0)
    max_w = max(len(l) for l in bio_lines)  # noqa: E741
    border = "═" * (max_w + 4)

    lines = [
        f"╔{border}╗",
        f"║  {'ZANA AEON':^{max_w}}  ║",
        f"╠{border}╣",
    ]
    for l in bio_lines:  # noqa: E741
        lines.append(f"║  {l:<{max_w}}  ║")
    lines += [
        f"╠{border}╣",
        f"║  {'Nombre:  ' + profile.name:<{max_w}}  ║",
        f"║  {'Arquetipo: ' + profile.archetype_name:<{max_w}}  ║",
        f"║  {'Etapa:   ' + profile.stage_label:<{max_w}}  ║",
        f"║  {'Días:    ' + str(profile.days_alive):<{max_w}}  ║",
        f"║  {'Memorias: ' + str(profile.memory_count):<{max_w}}  ║",
        f"║  {'DNA: ' + dna.birth_hash + '  H=' + str(dna.entropy):<{max_w}}  ║",
        f"╚{border}╝",
        f"  ⟡ {profile.archetype_tagline} ⟡",
        f"  {profile.cognitive_summary}",
        "  pip install zana  ·  zana.vecanova.com",
    ]
    card_text = "\n".join(lines)

    console.print(f"\n[{pc}]{card_text}[/{pc}]")

    if export:
        card_path = Path.home() / ".zana" / "aeon_card.txt"
        card_path.write_text(card_text)
        console.print(
            f"\n[success]✓[/success] Guardado en [accent]{card_path}[/accent]"
        )
        console.print("[muted]  Cópialo y compártelo — es tuyo.[/muted]")


def cmd_resonance() -> None:
    from zana.tui.aeon_dna import AeonProfile, derive_dna
    from zana.tui.resonance import run_resonance_test

    profile = AeonProfile.load()
    archetype = run_resonance_test(profile)
    profile.archetype = archetype
    # Re-derive DNA with new archetype (constraints change)
    profile.dna = derive_dna(profile.name, profile.init_at, archetype)
    profile.save()
    console.print(
        f"\n[success]✓[/success] Arquetipo [bold]{profile.archetype_name}[/bold] + DNA derivado "
        f"— guardados en [accent]~/.zana/[/accent]"
    )
    console.print(
        "[muted]  Usa [accent]zana aeon habitat[/accent] para ver tu Aeón vivo.[/muted]\n"
    )


def cmd_status() -> None:
    registry = _load_registry()
    active_id = _active_aeon_id()
    aeon = next((a for a in registry["aeons"] if a["id"] == active_id), None)

    if not aeon:
        console.print(
            f"[warning]Active Aeon '{active_id}' not found in registry.[/warning]"
        )
        raise typer.Exit(1)

    cost_c = COST_COLOR.get(aeon["cost_tier"], "white")
    lat_i = LATENCY_ICON.get(aeon["latency"], "?")

    console.print(
        Panel(
            f"[accent]{aeon['icon']}  {aeon['name']}[/accent]    [muted](id: {aeon['id']})[/muted]\n\n"
            f"[white]{aeon['tagline']}[/white]\n\n"
            f"[muted]Model:[/muted]    {aeon['model']}\n"
            f"[muted]Cost:[/muted]     [{cost_c}]{aeon['cost_tier']}[/{cost_c}]\n"
            f"[muted]Speed:[/muted]    {lat_i} {aeon['latency']}\n"
            f"[muted]Tools:[/muted]    {', '.join(aeon['tools'])}",
            title="[header] ACTIVE AEON [/header]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def cmd_resonance() -> None:  # noqa: F811
    """Forges an Aeon using the KORU-GENOME v4.0 protocol."""
    from zana.tui.resonance import ResonanceProtocol

    protocol = ResonanceProtocol()
    profile = protocol.run()
    if profile:
        # Save to registry or a special personal_aeons list
        pass


def cmd_export(output_path: Path | None = None) -> None:
    """Exports the active Aeon DNA to a portable .aeon file."""
    profile_path = Path.home() / ".zana" / "aeon_profile.json"
    if not profile_path.exists():
        console.print(
            "[error]No forged Aeon found. Run `zana aeon resonance` first.[/error]"
        )
        return

    profile = json.loads(profile_path.read_text())
    name = profile["name"]

    if not output_path:
        output_path = Path.cwd() / f"{name}.aeon"

    # Add AEP metadata
    aep_packet = {
        "aep_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "profile": profile,
    }

    output_path.write_text(json.dumps(aep_packet, indent=2))
    console.print(
        f"[success]✓ Aeon {name} exported to [bold]{output_path}[/bold][/success]"
    )


def cmd_summon(aeon_file: Path) -> None:
    """Summons an external Aeon from a .aeon file."""
    if not aeon_file.exists():
        console.print(f"[error]File not found: {aeon_file}[/error]")
        return

    try:
        packet = json.loads(aeon_file.read_text())
        profile = packet["profile"]
        console.print(
            Panel(
                f"[bold cyan]{profile['name']}[/bold cyan]\n"
                f"Archetype: {profile['archetype']}\n"
                f"Birth Hash: {profile['birth_hash'][:16]}...",
                title="Summoning Successful",
                border_style="green",
            )
        )

        # Save to ~/.zana/summons/
        summon_dir = Path.home() / ".zana" / "summons"
        summon_dir.mkdir(parents=True, exist_ok=True)
        (summon_dir / f"{profile['name']}.json").write_text(
            json.dumps(profile, indent=2)
        )

    except Exception as e:
        console.print(f"[error]Failed to summon Aeon: {e}[/error]")


# ── Gene metadata for tune ────────────────────────────────────────────────────

_GENE_META: list[tuple[str, str, str, float, float, type]] = [
    # (field, label, layer, min, max, type)
    ("g0_branch_angle", "branch_angle", "Fenotipo", 10.0, 75.0, float),
    ("g1_depth", "depth", "Fenotipo", 2.0, 7.0, int),
    ("g2_trunk_length", "trunk_length", "Fenotipo", 3.0, 10.0, float),
    ("g3_attenuation", "attenuation", "Fenotipo", 0.40, 0.85, float),
    ("g4_symmetry", "symmetry", "Fenotipo", 0.0, 3.0, int),
    ("g5_fork", "fork", "Fenotipo", 2.0, 3.0, int),
    ("g6_bend_drift", "bend_drift", "Fenotipo", -15.0, 15.0, float),
    ("g7_terminal_form", "terminal_form", "Fenotipo", 0.0, 5.0, int),
    ("g8_armor_density", "armor_density", "Fenotipo", 0.0, 1.0, float),
    ("g9_curiosity", "curiosity", "Cognitivo", 0.0, 9.0, float),
    ("g10_tenacity", "tenacity", "Cognitivo", 0.0, 9.0, float),
    ("g11_empathy", "empathy", "Cognitivo", 0.0, 9.0, float),
    ("g12_creativity", "creativity", "Cognitivo", 0.0, 9.0, float),
    ("g13_precision", "precision", "Cognitivo", 0.0, 9.0, float),
    ("g14_resilience", "resilience", "Cognitivo", 0.0, 9.0, float),
    ("g15_sovereignty", "sovereignty", "Cognitivo", 0.0, 9.0, float),
    ("g16_growth_rate", "growth_rate", "Evolutivo", 0.5, 2.0, float),
    ("g17_memory_affinity", "memory_affinity", "Evolutivo", 0.0, 1.0, float),
    ("g18_skill_absorption", "skill_absorption", "Evolutivo", 0.0, 1.0, float),
    ("g19_ledger_depth", "ledger_depth", "Evolutivo", 3.0, 21.0, int),
    ("g20_social_vector", "social_vector", "Evolutivo", 0.0, 1.0, float),
]

_GENE_LABELS = {
    label: (field, gmin, gmax, gtype)
    for field, label, _, gmin, gmax, gtype in _GENE_META
}


def cmd_tune(gene: str | None = None) -> None:
    """Interactive DNA tuner — adjust individual Aeon genes."""
    from rich import box as rbox

    from zana.tui.aeon_dna import AeonProfile

    profile = AeonProfile.load()
    dna = profile.ensure_dna()
    pc = profile.primary_color

    if gene:
        # Single-gene mode: tune one gene directly
        gene = gene.lower().lstrip("g")
        # Normalize: accept "curiosity", "g9", "g9_curiosity", "9"
        target_field: str | None = None
        target_min = target_max = 0.0
        target_type: type = float

        for field, label, _layer, gmin, gmax, gtype in _GENE_META:
            gene_num = field[1:].split("_")[0]
            if gene in (label, field, gene_num, f"g{gene_num}"):
                target_field, target_min, target_max, target_type = (
                    field,
                    gmin,
                    gmax,
                    gtype,
                )
                break

        if not target_field:
            console.print(
                f"[error]Gen desconocido: '{gene}'. "
                f"Usa el nombre (ej. curiosity) o número (ej. 9).[/error]"
            )
            valid_names = ", ".join(label for _, label, *_ in _GENE_META)
            console.print(f"[muted]Genes disponibles: {valid_names}[/muted]")
            raise typer.Exit(1)

        current = getattr(dna, target_field)
        console.print(
            f"\n[{pc}]◈ Tuning[/{pc}] [white]{target_field}[/white]  "
            f"[muted]actual=[/muted][accent]{current}[/accent]  "
            f"[muted]rango=[/muted][dim][{target_min}, {target_max}][/dim]"
        )

        try:
            raw = typer.prompt(f"  Nuevo valor [{target_min}–{target_max}]")
            new_val = target_type(float(raw))
        except (ValueError, KeyboardInterrupt):
            console.print("[muted]Cancelado.[/muted]")
            return

        if not (target_min <= new_val <= target_max):
            console.print(
                f"[error]Valor {new_val} fuera del rango [{target_min}, {target_max}].[/error]"
            )
            raise typer.Exit(1)

        setattr(dna, target_field, new_val)
        dna.generation += 1
        dna.entropy = dna._compute_entropy()
        dna.save()
        profile.dna = dna
        profile.save()

        console.print(
            f"[success]✓[/success] [white]{target_field}[/white] "
            f"[muted]{current}[/muted] → [accent]{new_val}[/accent]  "
            f"[muted]Generación {dna.generation} · H={dna.entropy}[/muted]\n"
        )
        return

    # Interactive mode: browse all genes
    table = Table(
        show_header=True,
        header_style="bold white",
        box=rbox.SIMPLE_HEAD,
        padding=(0, 1),
        title=f"[{pc}]◈ {profile.name} — DNA Tune[/{pc}]",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Gen", style="bold white", width=20)
    table.add_column("Capa", style="dim", width=10)
    table.add_column("Actual", style="accent", width=8)
    table.add_column("Rango", style="dim", width=14)

    for i, (field, label, layer, gmin, gmax, gtype) in enumerate(_GENE_META):
        current = getattr(dna, field)
        fmt = str(int(current)) if gtype is int else f"{current:.2f}"
        table.add_row(
            str(i),
            f"g{field[1:].split('_')[0]} {label}",
            layer,
            fmt,
            f"[{gmin}, {gmax}]",
        )

    console.print()
    console.print(table)
    console.print(
        "\n[muted]Escribe el nombre del gen a modificar (ej. [accent]curiosity[/accent]) "
        "o [accent]q[/accent] para salir:[/muted]"
    )

    while True:
        try:
            gene_input = typer.prompt("  Gen").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("[muted]Saliendo del tuner.[/muted]")
            break

        if gene_input in ("q", "quit", "exit", "salir"):
            break

        # Re-invoke single-gene logic
        target_field = None
        target_min = target_max = 0.0
        target_type_local: type = float

        for field, label, _layer, gmin, gmax, gtype in _GENE_META:
            gene_num = field[1:].split("_")[0]
            if gene_input in (label, field, gene_num, f"g{gene_num}"):
                target_field, target_min, target_max, target_type_local = (
                    field,
                    gmin,
                    gmax,
                    gtype,
                )
                break

        if not target_field:
            console.print(
                f"[warning]Gen '{gene_input}' no encontrado. Intenta de nuevo.[/warning]"
            )
            continue

        current = getattr(dna, target_field)
        console.print(
            f"  [muted]actual=[/muted][accent]{current}[/accent]  "
            f"[muted]rango=[/muted][dim][{target_min}, {target_max}][/dim]"
        )

        try:
            raw = typer.prompt(f"  Nuevo valor [{target_min}–{target_max}]")
            new_val = target_type_local(float(raw))
        except (ValueError, KeyboardInterrupt):
            console.print("[muted]Omitido.[/muted]")
            continue

        if not (target_min <= new_val <= target_max):
            console.print(
                f"[warning]Fuera de rango. Debe estar en [{target_min}, {target_max}].[/warning]"
            )
            continue

        setattr(dna, target_field, new_val)
        dna.generation += 1
        dna.entropy = dna._compute_entropy()

        console.print(
            f"  [success]✓[/success] [white]{target_field}[/white] → [accent]{new_val}[/accent]"
        )

    dna.save()
    profile.dna = dna
    profile.save()
    console.print(
        f"\n[success]✓[/success] DNA guardado — "
        f"[muted]Generación {dna.generation} · H={dna.entropy}[/muted]\n"
    )
