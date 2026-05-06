import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from cli.tui.aeon_battle import WORLDS, BattleEngine
from cli.tui.aeon_dna import derive_dna
from cli.tui.theme import console

app = typer.Typer(help="AEON MULTIVERSE — The First Artificial Life Coliseum.")

@app.command("worlds")
def cmd_worlds():
    """Lists all available worlds in the Aeon Multiverse."""
    table = Table(title="Mundos del Multiverso", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Nombre", style="bold white")
    table.add_column("Afinidad", style="green")
    table.add_column("Descripción", style="muted")

    for id, w in WORLDS.items():
        table.add_row(id, w.name, w.native_archetype.name, w.description)

    console.print(table)

@app.command("enter")
def cmd_enter(
    world_id: Annotated[str, typer.Argument(help="ID of the world to enter (e.g. fuego, calculo)")] = "fuego",
):
    """Enters a world and battles a deterministic AI guardian."""
    profile_path = Path.home() / ".zana" / "aeon_profile.json"
    if not profile_path.exists():
        console.print("[error]No forged Aeon found. Run `zana aeon resonance` first.[/error]")
        return

    profile = json.loads(profile_path.read_text())
    engine = BattleEngine(world_id)
    
    # Generate deterministic AI guardian for the world
    guardian_dna = derive_dna("GUARDIAN", engine.world.native_archetype, birth_seed=12345)
    guardian = {
        "name": f"Guardián de {engine.world.name.split()[-1]}",
        "dna": guardian_dna.to_dict()
    }
    
    result = engine.run_battle(profile, guardian)
    
    if result["winner"] == profile["name"]:
        console.print(f"\n[success]¡VICTORIA! {profile['name']} ha conquistado {engine.world.name}[/success]")
    else:
        console.print("\n[error]DERROTA. El guardián ha prevalecido.[/error]")

@app.command("challenge")
def cmd_challenge(
    aeon_name: Annotated[str, typer.Argument(help="Name of the summoned Aeon to challenge")]
):
    """Challenges a previously summoned Aeon to a duel."""
    profile_path = Path.home() / ".zana" / "aeon_profile.json"
    summon_path = Path.home() / ".zana" / "summons" / f"{aeon_name}.json"
    
    if not profile_path.exists():
        console.print("[error]No forged Aeon found. Run `zana aeon resonance` first.[/error]")
        return
    if not summon_path.exists():
        console.print(f"[error]Aeon '{aeon_name}' not found in summons. Use `zana aeon summon` first.[/error]")
        return

    profile = json.loads(profile_path.read_text())
    opponent = json.loads(summon_path.read_text())
    
    engine = BattleEngine("vacio") # Default world for duels
    engine.run_battle(profile, opponent)
