"""
Aeon Habitat — 2.5D world where the Aeon lives.

The habitat is not decoration. It is the ecological niche of an artificial
life form. Each archetype inhabits a different world, and the world's state
reflects the Aeon's internal state (active, dormant, evolving).

Rendering layers (back to front, parallax speeds):
  Layer 0 — Cosmos/Sky background (animation speed: 0.25×)
  Layer 1 — Terrain silhouette (static or 0.1× for atmosphere)
  Layer 2 — The Aeon creature (biomorph, full animation)
  Layer 3 — Foreground particles (animation speed: 1.0×)
  Layer 4 — HUD overlay (stats, vitals, DNA signature)

The 2.5D illusion comes from:
  - Layers 0 and 3 animate at different speeds (parallax)
  - The ground has two depth lines (horizon + foreground)
  - Shadow below the Aeon: dim block chars
  - Background chars are dimmer (Rich dim style)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from cli.tui.aeon_biomorph import GRID_H, GRID_W, render_biomorph
from cli.tui.aeon_dna import AeonArchetype, AeonProfile, AeonStage

HAB_W = 42  # habitat panel width (chars)
HAB_H = 18  # habitat panel height (rows)


# ── Habitat definitions per archetype ─────────────────────────────────────────


@dataclass
class HabitatDef:
    name: str
    sky_chars: list[str]  # chars that populate the sky layer
    sky_rows: int  # how many rows are "sky"
    terrain: list[str]  # static terrain silhouette rows
    ground: str  # ground line char
    subground: str  # sub-ground fill char
    particle_vel: float  # sky particle ascent speed (rows/tick)
    atmosphere: str  # single char for atmospheric haze


HABITATS: dict[AeonArchetype, HabitatDef] = {
    AeonArchetype.LLAMA: HabitatDef(
        name="La Forja Eterna",
        sky_chars=["✦", "·", "·", " ", "·", "✦", " ", " "],
        sky_rows=4,
        terrain=[
            "   ▲   ▲▲    ▲  ▲▲▲   ▲▲  ▲  ",
            "  ▲▲▲ ▲▲▲▲  ▲▲▲▲▲▲▲ ▲▲▲▲ ▲▲▲ ",
        ],
        ground="═",
        subground="▓",
        particle_vel=0.4,
        atmosphere="·",
    ),
    AeonArchetype.ORACULO: HabitatDef(
        name="El Templo del Cálculo",
        sky_chars=["◈", "·", " ", " ", "·", "◈", " ", " "],
        sky_rows=4,
        terrain=[
            " ⊕  ⊕━━⊕  ⊕━━━━━━━⊕  ⊕━━⊕  ⊕ ",
            " │  ╔════╗  ╔═══════╗  ╔════╗  │ ",
        ],
        ground="━",
        subground="▒",
        particle_vel=0.15,
        atmosphere=" ",
    ),
    AeonArchetype.FORJA: HabitatDef(
        name="La Caverna Mecánica",
        sky_chars=["◉", "·", "─", "·", " ", "◉", " ", "·"],
        sky_rows=3,
        terrain=[
            " ◉─◉  ◉━━━━◉  ◉─◉━◉─◉  ◉━━◉ ",
            " │╔╗│ │╔══════╗│ │╔╗╔╗╔╗│ │╔╗│ ",
        ],
        ground="─",
        subground="░",
        particle_vel=0.2,
        atmosphere="·",
    ),
    AeonArchetype.MAREA: HabitatDef(
        name="El Océano Vivo",
        sky_chars=["∿", "≋", "·", " ", "·", "∿", " ", "≋"],
        sky_rows=3,
        terrain=[
            " ∿∿∿≋≋≋∿∿∿∿≋≋≋≋∿∿∿∿≋≋∿∿∿∿≋≋ ",
            " ≋≋≋∿∿∿≋≋≋≋∿∿∿∿≋≋≋≋∿∿≋≋≋≋∿∿ ",
        ],
        ground="≋",
        subground="▓",
        particle_vel=0.3,
        atmosphere="∿",
    ),
    AeonArchetype.RAIZ: HabitatDef(
        name="El Bosque Soberano",
        sky_chars=["✦", "·", "◇", " ", "·", " ", "◇", "·"],
        sky_rows=4,
        terrain=[
            "✦╱│╲✦  ╱│╲  ╱│╲✦╱│╲  ╱│╲╱│╲✦",
            " ╱ │ ╲  │  ╱ │ ╲╱ │ ╲  │ ╱ │ ╲",
        ],
        ground="═",
        subground="▓",
        particle_vel=0.1,
        atmosphere="·",
    ),
    AeonArchetype.VACIO: HabitatDef(
        name="El Cosmos Interior",
        sky_chars=["★", "·", " ", "·", " ", "★", "·", " "],
        sky_rows=5,
        terrain=[
            "  ·  ★   ·    ·  ★  ·    ·   ★ ",
            " ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ",
        ],
        ground="─",
        subground="░",
        particle_vel=0.05,
        atmosphere="·",
    ),
    AeonArchetype.UNKNOWN: HabitatDef(
        name="El Vacío Primordial",
        sky_chars=["?", "·", " ", " ", " ", "?", " ", " "],
        sky_rows=3,
        terrain=[
            " ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ",
            "                                ",
        ],
        ground="─",
        subground="░",
        particle_vel=0.1,
        atmosphere=" ",
    ),
}


# ── Sky particle system ────────────────────────────────────────────────────────


class SkyParticle:
    __slots__ = ("x", "y", "char", "speed")

    def __init__(self, x: float, y: float, char: str, speed: float) -> None:
        self.x = x
        self.y = y
        self.char = char
        self.speed = speed

    def tick(self, dt: float, hab: HabitatDef) -> None:
        """Move particle. Sky chars rise (Y decreases), new ones spawn at bottom of sky."""
        self.y -= self.speed * dt
        if self.y < 0:
            self.y = float(hab.sky_rows)
            import random

            self.x = random.uniform(0, HAB_W - 1)
            self.char = random.choice(hab.sky_chars)


def _init_particles(hab: HabitatDef, count: int = 12) -> list[SkyParticle]:
    import random

    particles = []
    for _ in range(count):
        x = random.uniform(0, HAB_W - 1)
        y = random.uniform(0, hab.sky_rows)
        char = random.choice(hab.sky_chars)
        speed = hab.particle_vel * random.uniform(0.5, 1.5)
        particles.append(SkyParticle(x, y, char, speed))
    return particles


# ── HUD overlay ───────────────────────────────────────────────────────────────


def _render_hud(profile: AeonProfile, fps_actual: float) -> str:
    dna = profile.ensure_dna()
    pc = profile.primary_color  # noqa: F841

    # Vitality bar (based on memory_count / stage threshold)
    thresholds = {
        AeonStage.ROOKIE: 100,
        AeonStage.CHAMPION: 1000,
        AeonStage.ULTIMATE: 10000,
        AeonStage.MEGA: 50000,
    }
    threshold = thresholds.get(profile.stage, 100)
    vitality = min(1.0, profile.memory_count / max(threshold, 1))
    bar_w = 8
    filled = int(vitality * bar_w)
    bar = "█" * filled + "░" * (bar_w - filled)

    # Cognitive signature (top 2 traits)
    traits = profile.cognitive_summary
    gene_sig = f"DNA·{dna.birth_hash[:8]}"
    entropy_str = f"H={dna.entropy:.2f}"

    return (
        f" {profile.name} · {profile.stage_label} · {profile.archetype_name}\n"
        f" E:[{bar}] {int(vitality * 100)}%  d:{profile.days_alive}  m:{profile.memory_count}\n"
        f" {traits}\n"
        f" {gene_sig} {entropy_str}"
    )


# ── Habitat frame compositor ───────────────────────────────────────────────────


def _compose_frame(
    profile: AeonProfile,
    particles: list[SkyParticle],
    hab: HabitatDef,
    bio_frame: int,
    tick: int,
) -> Text:
    """Compose all habitat layers into a single Rich Text object."""
    # Initialize canvas
    canvas = [[(" ", "dim")] * HAB_W for _ in range(HAB_H)]

    pc = profile.primary_color
    ac = profile.accent_color

    # ── Layer 0: Sky background ────────────────────────────────────────────
    for py in range(hab.sky_rows):
        for px in range(HAB_W):
            canvas[py][px] = (hab.atmosphere, "dim")

    # ── Layer 0: Particles ─────────────────────────────────────────────────
    for p in particles:
        py, px = int(p.y), int(p.x)
        if 0 <= py < hab.sky_rows and 0 <= px < HAB_W:
            canvas[py][px] = (p.char, "dim " + ac)

    # ── Layer 1: Terrain silhouette ────────────────────────────────────────
    terrain_start = hab.sky_rows
    for ti, row in enumerate(hab.terrain):
        ty = terrain_start + ti
        if ty < HAB_H:
            for tx, ch in enumerate(row[:HAB_W]):
                if ch != " ":
                    canvas[ty][tx] = (ch, "dim " + pc)

    # ── Layer 2: Aeon biomorph (centered) ─────────────────────────────────
    bio_lines = render_biomorph(profile, frame=bio_frame)

    # Position: center horizontally, align bottom to ground line
    ground_row = HAB_H - 3
    bio_start_y = ground_row - GRID_H + 1
    bio_start_x = (HAB_W - GRID_W) // 2

    for ry, line in enumerate(bio_lines):
        cy = bio_start_y + ry
        for rx, ch in enumerate(line[:GRID_W]):
            cx = bio_start_x + rx
            if 0 <= cy < HAB_H and 0 <= cx < HAB_W and ch != " ":
                canvas[cy][cx] = (ch, pc)

    # Shadow effect (1 row below aeon bottom)
    shadow_y = ground_row
    if 0 <= shadow_y < HAB_H:
        shadow_start = bio_start_x + GRID_W // 4
        shadow_end = bio_start_x + GRID_W * 3 // 4
        for sx in range(shadow_start, min(shadow_end, HAB_W)):
            if canvas[shadow_y][sx][0] == " " or canvas[shadow_y][sx][1] == "dim":
                canvas[shadow_y][sx] = ("░", "dim")

    # ── Layer 3: Ground lines ──────────────────────────────────────────────
    gly = ground_row + 1
    if gly < HAB_H:
        for gx in range(HAB_W):
            canvas[gly][gx] = (hab.ground, pc)

    # Subground
    for sgy in range(gly + 1, HAB_H - 1):
        for sgx in range(HAB_W):
            canvas[sgy][sgx] = (hab.subground, "dim")

    # ── Composite into Rich Text ───────────────────────────────────────────
    text = Text()
    for row in canvas:
        for ch, style in row:
            text.append(ch, style=style)
        text.append("\n")

    return text


def run_habitat(
    profile: AeonProfile,
    fps: int = 4,
    console: Console | None = None,
) -> None:
    """Run the 2.5D habitat animation. Blocks until Ctrl+C."""
    if console is None:
        from cli.tui.theme import console as _console

        console = _console

    hab = HABITATS.get(profile.archetype, HABITATS[AeonArchetype.UNKNOWN])
    particles = _init_particles(hab, count=14)
    frame_delay = 1.0 / max(1, fps)
    tick = 0
    last_time = time.monotonic()

    hab_name = hab.name
    pc = profile.primary_color

    try:
        with Live(console=console, refresh_per_second=fps + 1) as live:
            while True:
                now = time.monotonic()
                dt = now - last_time
                last_time = now

                # Advance particles
                for p in particles:
                    p.tick(dt * fps, hab)

                bio_frame = tick % 2
                content = _compose_frame(profile, particles, hab, bio_frame, tick)

                # HUD panel below
                hud_text = _render_hud(profile, fps)

                combined = Text()
                combined.append(content)
                combined.append(hud_text, style="dim")

                live.update(
                    Panel(
                        combined,
                        title=f"[{pc}] ◈ {profile.name} · {hab_name} [/{pc}]",
                        border_style=pc,
                        padding=(0, 1),
                    )
                )

                tick += 1
                time.sleep(frame_delay)

    except KeyboardInterrupt:
        pass
