import hashlib
import struct
import time
from dataclasses import dataclass
from typing import Any

from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from zana.tui.aeon_dna import AeonArchetype, AeonDNA
from zana.tui.theme import console


@dataclass
class World:
    name: str
    native_archetype: AeonArchetype
    description: str


WORLDS = {
    "fuego": World(
        "El Coliseo del Fuego",
        AeonArchetype.MALKHUT,
        "Combate directo, tenacidad extrema.",
    ),
    "calculo": World(
        "El Ágora del Cálculo", AeonArchetype.CHOKHMAH, "Lógica y precisión matemática."
    ),
    "forja": World(
        "La Gran Forja", AeonArchetype.BINAH, "Construcción y resistencia física."
    ),
    "oceano": World(
        "El Océano Abierto", AeonArchetype.NETZACH, "Alianzas, fluidez y diplomacia."
    ),
    "floresta": World(
        "La Floresta Eterna", AeonArchetype.YESOD, "Memoria, raíces y paciencia."
    ),
    "vacio": World(
        "El Vacío Profundo", AeonArchetype.DAAT, "Exploración, sombras e incertidumbre."
    ),
}


@dataclass
class CombatStats:
    hp: float
    attack: float
    defense: float
    initiative: float
    special: float
    accuracy: float
    reputation_bonus: float


class BattleEngine:
    """
    Deterministic Battle Engine for Aeon Multiverse.
    No RNG during battle. Results are calculated using DNA hashes and round seeds.
    """

    def __init__(self, world_id: str = "fuego"):
        self.world = WORLDS.get(world_id, WORLDS["fuego"])

    def compute_stats(self, dna: AeonDNA) -> CombatStats:
        world_mult = (
            1.25 if dna.g24_world_affinity == int(self.world.native_archetype) else 1.0
        )

        # Base stats derived from Layers 2 & 4
        attack = (
            (
                dna.g10_tenacity * 0.4
                + dna.g12_creativity * 0.3
                + dna.g13_precision * 0.2
                + dna.g8_armor_density * 0.1
            )
            * world_mult
            * 20
        )

        defense = (
            (
                dna.g14_resilience * 0.4
                + dna.g8_armor_density * 0.3
                + dna.g15_sovereignty * 0.2
                + dna.g10_tenacity * 0.1
            )
            * world_mult
            * 20
        )

        initiative = (
            dna.g9_curiosity * 0.5
            + dna.g16_growth_rate * 0.3
            + dna.g23_adaptation_rate * 0.2
        ) * 10

        special = dna.g12_creativity * 25
        accuracy = dna.g13_precision * 0.8 + dna.g34_luck_constant * 0.2
        reputation_bonus = min(5.0, dna.g25_reputation * 0.1)

        return CombatStats(
            hp=100.0,
            attack=attack,
            defense=defense,
            initiative=initiative,
            special=special,
            accuracy=accuracy,
            reputation_bonus=reputation_bonus,
        )

    def _get_move(self, dna: AeonDNA, round_n: int, opponent_hash: str) -> str:
        """Deterministic move selection."""
        moves = [
            "Ataque Básico",
            "Defensa Firme",
            "Habilidad Especial",
            "Maniobra Evasiva",
        ]
        seed = f"{dna.get_hash()}_{round_n}_{opponent_hash}"
        digest = hashlib.sha256(seed.encode()).digest()
        idx = struct.unpack(">Q", digest[:8])[0] % len(moves)
        return moves[idx]

    def run_battle(
        self, aeon_a: dict[str, Any], aeon_b: dict[str, Any]
    ) -> dict[str, Any]:
        dna_a = AeonDNA(**aeon_a["dna"])
        dna_b = AeonDNA(**aeon_b["dna"])

        stats_a = self.compute_stats(dna_a)
        stats_b = self.compute_stats(dna_b)

        log = []  # noqa: F841
        hp_a, hp_b = 100.0, 100.0

        console.print(
            Panel(
                f"[bold yellow]{self.world.name}[/bold yellow]\n{self.world.description}",
                title="Arena",
                border_style="blue",
            )
        )

        with Live(
            self._render_battle_state(aeon_a["name"], aeon_b["name"], hp_a, hp_b, 0),
            refresh_per_second=4,
        ) as live:
            for r in range(1, 6):
                time.sleep(1)

                move_a = self._get_move(dna_a, r, dna_b.get_hash())
                move_b = self._get_move(dna_b, r, dna_a.get_hash())

                # Simple damage formula
                dmg_a = max(
                    2,
                    (stats_a.attack - stats_b.defense * 0.5)
                    * (1 if move_a != "Defensa Firme" else 0.5),
                )
                dmg_b = max(
                    2,
                    (stats_b.attack - stats_a.defense * 0.5)
                    * (1 if move_b != "Defensa Firme" else 0.5),
                )

                if move_a == "Habilidad Especial":
                    dmg_a += stats_a.special * 0.5
                if move_b == "Habilidad Especial":
                    dmg_b += stats_b.special * 0.5

                hp_b -= dmg_a
                hp_a -= dmg_b

                hp_a = max(0, hp_a)
                hp_b = max(0, hp_b)

                live.update(
                    self._render_battle_state(
                        aeon_a["name"], aeon_b["name"], hp_a, hp_b, r, move_a, move_b
                    )
                )

                if hp_a <= 0 or hp_b <= 0:
                    break

        winner = aeon_a["name"] if hp_a > hp_b else aeon_b["name"]
        return {"winner": winner, "hp_a": hp_a, "hp_b": hp_b, "rounds": r}

    def _render_battle_state(
        self, name_a, name_b, hp_a, hp_b, round_n, move_a="", move_b=""
    ):
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")

        bar_a = f"[green]{'█' * int(hp_a / 10)}{'░' * (10 - int(hp_a / 10))}[/green]"
        bar_b = f"[red]{'█' * int(hp_b / 10)}{'░' * (10 - int(hp_b / 10))}[/red]"

        table.add_row(
            f"[bold cyan]{name_a}[/bold cyan]\n{bar_a} {hp_a:.1f}%",
            f"[bold white]RONDA {round_n}[/bold white]",
            f"[bold magenta]{name_b}[/bold magenta]\n{hp_b:.1f}% {bar_b}",
        )

        if move_a or move_b:
            table.add_row(
                f"[italic]{move_a}[/italic]", "vs", f"[italic]{move_b}[/italic]"
            )

        return Panel(table, title="Coliseo Aeon", border_style="magenta")
