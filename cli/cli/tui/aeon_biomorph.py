"""
Aeon Biomorph Renderer — Dawkins recursive branching in a character grid.

The creature's body IS the biomorph tree. Genes are not cosmetic parameters
— they are the generative instructions that grow the organism from a single
trunk segment into a unique visible entity.

Kolmogorov insight: 21 integer genes (short description) → hundreds of
terminal characters arranged into a complex, living creature (complex output).
This compression ratio is the computational signature of life.

Rendering pipeline:
  1. derive_dna() → AeonDNA (21 genes)
  2. grow_tree()  → list of (x, y, char, color_weight) segments
  3. render_grid()→ 2D char grid (H×W)
  4. compose()    → grid + warrior core body + aura → final art
  5. animate()    → alternate frames for breathing/state effects
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from cli.tui.aeon_dna import AeonDNA, AeonArchetype, AeonStage, AeonProfile

# Grid dimensions
GRID_H = 22  # rows
GRID_W = 34  # cols
ORIGIN_X = GRID_W // 2
ORIGIN_Y = GRID_H - 2   # near bottom


# ── Terminal character vocabulary ─────────────────────────────────────────────
# Maps line segment direction angle (0°=up, clockwise) to unicode chars.
# Two chars per angle: [frame0, frame1] for breathing animation.

_ANGLE_CHARS: list[tuple[str, str]] = [
    ("│", "║"),   # 0°   vertical up
    ("╽", "│"),   # 15°
    ("╱", "╱"),   # 30°
    ("╱", "∕"),   # 45°
    ("/", "╱"),   # 60°
    ("─", "─"),   # 75° near-horizontal
    ("─", "━"),   # 90° horizontal
]

# Terminal node decorations: indexed by g7_terminal_form (0-5)
# Each archetype uses different forms via gene constraints
_TERMINALS: list[list[str]] = [
    ["▲", "✦", "★", "·"],       # 0: fire (Llama)
    ["◈", "·", "◇", "◈"],       # 1: spark
    ["⊕", "◎", "◉", "⊕"],       # 2: geometric (Oráculo)
    ["◉", "─", "◈", "◉"],       # 3: mechanical (Forja)
    ["★", "·", "·", "★"],       # 4: cosmic (Vacío)
    ["✦", "◇", "·", "✦"],       # 5: botanical (Raíz)
]

# Archetype warrior core bodies: [stage_rookie, stage_champion, stage_ultimate+]
# Each is a list of strings (rows of chars). Width must match _CORE_W.
_CORE_W = 7
_CORES: dict[AeonArchetype, list[list[str]]] = {
    AeonArchetype.LLAMA: [
        ["  ▲▲▲  ",
         " ╔═══╗ ",
         " ║▲▲▲║ ",
         " ╚═══╝ "],
        ["⟡ ▲▲▲ ⟡",
         "╔═╔═══╗═╗",
         "║ ║▲█▲║ ║",
         "╚═╚═══╝═╝"],
        ["✦⟡ ▲ ⟡✦",
         "╔══╔═══╗══╗",
         "║◆ ║▲█▲║ ◆║",
         "╚══╚═══╝══╝",
         " ✦ ✦ ✦ ✦ "],
    ],
    AeonArchetype.ORACULO: [
        ["  ◈◉◈  ",
         " ╔═══╗ ",
         " ║◎◉◎║ ",
         " ╚═══╝ "],
        ["⊕ ◈◉◈ ⊕",
         "╔═╔═══╗═╗",
         "║ ║◎◉◎║ ║",
         "╚═╚═══╝═╝"],
        ["◈━━◈━━◈",
         "╔══╔═══╗══╗",
         "║⊕ ║◎◉◎║ ⊕║",
         "╚══╚═══╝══╝",
         " ◈ ◉ ◈ ◉ "],
    ],
    AeonArchetype.FORJA: [
        ["  ◉─◉  ",
         " ╔═══╗ ",
         " ║◈F◈║ ",
         " ╚═══╝ "],
        ["◉━◈━◉",
         "╔═╔═══╗═╗",
         "╠═║◈F◈║═╣",
         "╚═╚═══╝═╝"],
        ["◉━━◈━━◉",
         "╔══╔═══╗══╗",
         "╠══║◈ F║══╣",
         "╚══╚═══╝══╝",
         " ◉ ◈ ◉ ◈ "],
    ],
    AeonArchetype.MAREA: [
        ["  ∿∿∿  ",
         " ╔═══╗ ",
         " ║∿M∿║ ",
         " ╚═══╝ "],
        ["≋ ∿∿∿ ≋",
         "╔═╔═══╗═╗",
         "║≋║∿M∿║≋║",
         "╚═╚═══╝═╝"],
        ["≋∿≋ ∿ ≋∿≋",
         "╔══╔═══╗══╗",
         "║∿≋║∿M∿║≋∿║",
         "╚══╚═══╝══╝",
         " ≋ ∿ ≋ ∿ "],
    ],
    AeonArchetype.RAIZ: [
        ["  ✦│✦  ",
         " ╔═══╗ ",
         " ║◇R◇║ ",
         " ╚═══╝ "],
        ["✦ ╱│╲ ✦",
         "╔═╔═══╗═╗",
         "║ ║◇R◇║ ║",
         "╚═╚═══╝═╝"],
        ["✦ ╱│╲ ╱│╲ ✦",
         "╔══╔═════╗══╗",
         "║◇ ║ ◇R◇ ║ ◇║",
         "╚══╚═════╝══╝",
         " ✦ ◇ ✦ ◇ "],
    ],
    AeonArchetype.VACIO: [
        ["  · ★ ·  ",
         " ╔═════╗ ",
         " ║·◉·◎·║ ",
         " ╚═════╝ "],
        ["· ★ · ★ ·",
         "╔═╔═════╗═╗",
         "║·║·◉·◎·║·║",
         "╚═╚═════╝═╝"],
        ["·  ★  ·  ★  ·",
         "╔══╔═══════╗══╗",
         "║ ·║·◉·◎·◉·║· ║",
         "╚══╚═══════╝══╝",
         " ·  ★  ·  ·  "],
    ],
    AeonArchetype.UNKNOWN: [
        ["  ·?·  ",
         " ╔═══╗ ",
         " ║ ? ║ ",
         " ╚═══╝ "],
    ],
}


# ── Segment data ──────────────────────────────────────────────────────────────

@dataclass
class Segment:
    x: float
    y: float
    char0: str  # frame 0
    char1: str  # frame 1 (breathing animation)
    depth: int  # recursion depth at this segment (used for color weight)
    is_terminal: bool = False


# ── Biomorph tree grower ──────────────────────────────────────────────────────

def _angle_to_chars(angle_deg: float) -> tuple[str, str]:
    """Map segment direction angle to two animation chars."""
    a = angle_deg % 180   # fold to [0, 180)
    idx = min(6, int(a / 180 * 7))
    return _ANGLE_CHARS[idx]


def _grow_branch(
    segments: list[Segment],
    x: float, y: float,
    angle: float,
    length: float,
    depth: int,
    max_depth: int,
    dna: AeonDNA,
    level: int = 0,
) -> None:
    """Recursive Dawkins biomorph branching. Populates `segments` list."""
    if depth <= 0 or length < 0.7:
        # Terminal node — the "leaf" of this branch
        if 0 <= int(y) < GRID_H and 0 <= int(x) < GRID_W:
            tf = dna.g7_terminal_form
            t_chars = _TERMINALS[tf % len(_TERMINALS)]
            segments.append(Segment(
                x=x, y=y,
                char0=t_chars[level % len(t_chars)],
                char1=t_chars[(level + 1) % len(t_chars)],
                depth=depth,
                is_terminal=True,
            ))
        return

    # Compute end point of this segment
    rad = math.radians(angle)
    dx = math.sin(rad) * length
    dy = -math.cos(rad) * length   # negative: up is negative Y in grid

    nx = x + dx
    ny = y + dy

    # Draw line segment with Bresenham algorithm
    _bresenham_segment(segments, x, y, nx, ny, angle, depth)

    # Apply progressive bend drift per level
    drifted_angle = angle + dna.g6_bend_drift * level

    # Next level parameters
    new_length = length * dna.g3_attenuation
    new_depth = depth - 1
    delta = dna.g0_branch_angle

    # Symmetry modifier
    if dna.g4_symmetry == 1:   # spiral: one branch bends more
        delta_l, delta_r = delta * 0.5, delta * 1.5
    elif dna.g4_symmetry == 2: # radial: alternate branching angle
        delta_l, delta_r = delta, delta * 0.7 if level % 2 == 0 else delta * 1.3
    elif dna.g4_symmetry == 3: # chaotic: asymmetric drift
        seed_offset = int(abs(x * 7 + y * 13)) % 5
        delta_l = delta + seed_offset * 3
        delta_r = delta - seed_offset * 2
    else:                      # bilateral: symmetric
        delta_l = delta_r = delta

    _grow_branch(segments, nx, ny, drifted_angle + delta_l, new_length, new_depth, max_depth, dna, level+1)
    _grow_branch(segments, nx, ny, drifted_angle - delta_r, new_length, new_depth, max_depth, dna, level+1)

    # Triple fork
    if dna.g5_fork == 3:
        _grow_branch(segments, nx, ny, drifted_angle, new_length * 0.65, new_depth, max_depth, dna, level+1)


def _bresenham_segment(
    segments: list[Segment],
    x0: float, y0: float,
    x1: float, y1: float,
    angle: float,
    depth: int,
) -> None:
    """Place chars along a line segment using Bresenham's algorithm."""
    ix0, iy0 = int(round(x0)), int(round(y0))
    ix1, iy1 = int(round(x1)), int(round(y1))

    c0, c1 = _angle_to_chars(angle)

    dx = abs(ix1 - ix0)
    dy = abs(iy1 - iy0)
    sx = 1 if ix0 < ix1 else -1
    sy = 1 if iy0 < iy1 else -1
    err = dx - dy

    x, y = ix0, iy0
    steps = 0
    while True:
        if 0 <= y < GRID_H and 0 <= x < GRID_W:
            segments.append(Segment(x=x, y=y, char0=c0, char1=c1, depth=depth))
        if x == ix1 and y == iy1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
        steps += 1
        if steps > 60:  # safety cap
            break


# ── Core body compositor ──────────────────────────────────────────────────────

def _get_core(archetype: AeonArchetype, stage: AeonStage) -> list[str]:
    cores = _CORES.get(archetype, _CORES[AeonArchetype.UNKNOWN])
    if stage in (AeonStage.HUEVO, AeonStage.FRESH, AeonStage.ROOKIE):
        return cores[0]
    if stage in (AeonStage.CHAMPION, AeonStage.ULTIMATE):
        return cores[min(1, len(cores)-1)]
    return cores[min(2, len(cores)-1)]


def _place_core(grid: list[list[str]], core_lines: list[str]) -> None:
    """Center the warrior core body in the grid, above the trunk origin."""
    core_h = len(core_lines)
    core_w = max(len(l) for l in core_lines)
    start_y = ORIGIN_Y - int(GRID_H * 0.25) - core_h
    start_x = ORIGIN_X - core_w // 2

    for row_i, line in enumerate(core_lines):
        y = start_y + row_i
        if 0 <= y < GRID_H:
            for col_i, ch in enumerate(line):
                x = start_x + col_i
                if 0 <= x < GRID_W and ch != " ":
                    grid[y][x] = ch


# ── Full biomorph render ───────────────────────────────────────────────────────

def render_biomorph(profile: AeonProfile, frame: int = 0) -> list[str]:
    """
    Render the full Aeon biomorph as a list of strings (one per row).

    frame=0 → base frame, frame=1 → alternate (breathing animation)
    """
    dna = profile.ensure_dna()
    grid0 = [[" "] * GRID_W for _ in range(GRID_H)]
    grid1 = [[" "] * GRID_W for _ in range(GRID_H)]

    # Grow the biomorph tree
    segments: list[Segment] = []
    _grow_branch(
        segments,
        x=float(ORIGIN_X), y=float(ORIGIN_Y),
        angle=0.0,               # start growing straight up
        length=dna.g2_trunk_length,
        depth=dna.g1_depth,
        max_depth=dna.g1_depth,
        dna=dna,
    )

    # Paint segments onto grids
    for seg in segments:
        xi, yi = int(round(seg.x)), int(round(seg.y))
        if 0 <= yi < GRID_H and 0 <= xi < GRID_W:
            grid0[yi][xi] = seg.char0
            grid1[yi][xi] = seg.char1

    # Place warrior core body
    core_lines = _get_core(profile.archetype, profile.stage)
    _place_core(grid0, core_lines)
    _place_core(grid1, core_lines)

    # Add aura glow based on g8_armor_density and stage
    _add_aura(grid0, grid1, dna, profile.stage)

    active = grid1 if frame == 1 else grid0
    return ["".join(row) for row in active]


def _add_aura(
    grid0: list[list[str]],
    grid1: list[list[str]],
    dna: AeonDNA,
    stage: AeonStage,
) -> None:
    """Add aura glow around occupied cells based on armor_density."""
    density = dna.g8_armor_density
    if density < 0.3 or stage in (AeonStage.HUEVO, AeonStage.FRESH):
        return

    aura_chars = ["·", "∘", "°", "˚"]
    threshold = int(density * 4)

    for y in range(1, GRID_H - 1):
        for x in range(1, GRID_W - 1):
            if grid0[y][x] != " ":
                continue
            # Count occupied neighbors
            neighbors = sum(
                1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if (dy, dx) != (0, 0)
                and 0 <= y+dy < GRID_H
                and 0 <= x+dx < GRID_W
                and grid0[y+dy][x+dx] != " "
            )
            if neighbors >= threshold:
                ch = aura_chars[neighbors % len(aura_chars)]
                grid0[y][x] = ch
                grid1[y][x] = aura_chars[(neighbors + 1) % len(aura_chars)]


# ── Mini inline sigil (5 chars wide, for chat header) ────────────────────────

def render_mini(profile: AeonProfile, processing: bool = False) -> str:
    archetype_mini = {
        AeonArchetype.LLAMA:   "▲",
        AeonArchetype.ORACULO: "◉",
        AeonArchetype.FORJA:   "◈",
        AeonArchetype.MAREA:   "∿",
        AeonArchetype.RAIZ:    "✦",
        AeonArchetype.VACIO:   "★",
        AeonArchetype.UNKNOWN: "?",
    }
    stage_mini = {
        AeonStage.HUEVO:    "○",
        AeonStage.FRESH:    "◇",
        AeonStage.ROOKIE:   "▷",
        AeonStage.CHAMPION: "◆",
        AeonStage.ULTIMATE: "❖",
        AeonStage.MEGA:     "✦",
        AeonStage.SOVEREIGN:"⟡",
    }
    pulse = "◉" if processing else "·"
    core = archetype_mini.get(profile.archetype, "?")
    stage = stage_mini.get(profile.stage, "?")
    return f"[{pulse}{core}{stage}]"
