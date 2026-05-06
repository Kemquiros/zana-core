"""
Aeon Sigil — Living visual representation of a sovereign Aeon.

Each Aeon is a unique organism: archetype determines morphology,
stage determines complexity, seed determines individual variation.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

AEON_HOME = Path.home() / ".zana"
AEON_PROFILE_PATH = AEON_HOME / "aeon_profile.json"
EPISODIC_DB = AEON_HOME / "episodic.db"


# ── Enums ─────────────────────────────────────────────────────────────────────

class AeonArchetype(str, Enum):
    LLAMA   = "llama"    # Fire — visionary, leader
    ORACULO = "oraculo"  # Sacred geometry — analytical
    FORJA   = "forja"    # Mechanical-organic — builder
    MAREA   = "marea"    # Fluid, no angles — connector
    RAIZ    = "raiz"     # Tree/mountain, fractal — guardian
    VACIO   = "vacio"    # Cosmos inverted — explorer
    UNKNOWN = "unknown"  # Pre-resonance test


class AeonStage(str, Enum):
    HUEVO     = "HUEVO"     # Hours 0-12: embryonic
    FRESH     = "FRESH"     # Days 1-3
    ROOKIE    = "ROOKIE"    # Days 4-30
    CHAMPION  = "CHAMPION"  # Days 31-180
    ULTIMATE  = "ULTIMATE"  # Days 181-365
    MEGA      = "MEGA"      # Days 366+
    SOVEREIGN = "SOVEREIGN" # MEGA + Z-Sync ON


class AeonState(str, Enum):
    IDLE       = "idle"
    PROCESSING = "processing"
    SLEEPING   = "sleeping"
    EVOLVING   = "evolving"


# ── Colors per archetype ───────────────────────────────────────────────────────

ARCHETYPE_COLORS = {
    AeonArchetype.LLAMA:   ("bright_red",    "gold1"),
    AeonArchetype.ORACULO: ("medium_purple", "bright_blue"),
    AeonArchetype.FORJA:   ("dark_orange",   "bright_yellow"),
    AeonArchetype.MAREA:   ("cyan",          "sea_green3"),
    AeonArchetype.RAIZ:    ("green",         "dark_olive_green3"),
    AeonArchetype.VACIO:   ("grey82",        "bright_white"),
    AeonArchetype.UNKNOWN: ("magenta",       "white"),
}

ARCHETYPE_LABELS = {
    AeonArchetype.LLAMA:   ("Llama",   "Visionario · Líder"),
    AeonArchetype.ORACULO: ("Oráculo", "Analítico · Contemplativo"),
    AeonArchetype.FORJA:   ("Forja",   "Constructor · Pragmático"),
    AeonArchetype.MAREA:   ("Marea",   "Conector · Empático"),
    AeonArchetype.RAIZ:    ("Raíz",    "Guardián · Sistemático"),
    AeonArchetype.VACIO:   ("Vacío",   "Explorador · Disruptor"),
    AeonArchetype.UNKNOWN: ("???",     "Resonancia pendiente"),
}


# ── Frame art per archetype × stage ───────────────────────────────────────────
# Each entry is a list of frames (for animation). Frame chars that vary between
# frames are the "breathing" pixels. All frames same line count.

def _frames_llama(stage: AeonStage, seed: int) -> list[list[str]]:
    name_deco = ["✦", "·", "⟡", "★"][seed % 4]
    if stage in (AeonStage.HUEVO, AeonStage.FRESH):
        return [
            ["    ◇    ",
             "   ╱▲╲   ",
             "  ◇ █ ◇  ",
             "    │    "],
            ["    ◇    ",
             "   ╱▲╲   ",
             "  ◇ ▲ ◇  ",
             "    │    "],
        ]
    if stage == AeonStage.ROOKIE:
        return [
            ["    ▲    ",
             "   ╱█╲   ",
             "  ◇ █ ◇  ",
             "    │    "],
            ["    ▲▲   ",
             "   ╱█╲   ",
             "  ◇ ▲ ◇  ",
             "    │    "],
        ]
    if stage == AeonStage.CHAMPION:
        return [
            [f" {name_deco} · {name_deco} ",
             " ╱╔═════╗╲",
             f" ║ ║▲█▲║ ║",
             " ╲╚═════╝╱",
             f" {name_deco} · {name_deco} "],
            [f" · {name_deco} · ",
             " ╱╔═════╗╲",
             f" ║ ║▲▲▲║ ║",
             " ╲╚═════╝╱",
             f" · {name_deco} · "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            [f"⟡ {name_deco} · {name_deco} ⟡",
             "╱╔═══════╗╲ ",
             f"║ ║▲█▲█▲║ ║",
             "╲╚═══════╝╱ ",
             f"⟡ {name_deco} · {name_deco} ⟡"],
            [f"· {name_deco} ⟡ {name_deco} ·",
             "╱╔═══════╗╲ ",
             f"║ ║▲▲█▲▲║ ║",
             "╲╚═══════╝╱ ",
             f"· {name_deco} ⟡ {name_deco} ·"],
        ]
    # MEGA / SOVEREIGN
    return [
        [f"⟡ {name_deco} ★ {name_deco} ⟡",
         "╱╔═════════╗╲",
         f"║ ║▲▲█▲▲▲║ ║",
         "╲╚═════════╝╱",
         f"⟡ {name_deco} ★ {name_deco} ⟡"],
        [f"★ {name_deco} ⟡ {name_deco} ★",
         "╱╔═════════╗╲",
         f"║ ║▲█▲▲█▲║ ║",
         "╲╚═════════╝╱",
         f"★ {name_deco} ⟡ {name_deco} ★"],
    ]


def _frames_oraculo(stage: AeonStage, seed: int) -> list[list[str]]:
    if stage in (AeonStage.HUEVO, AeonStage.FRESH):
        return [["  ◈  ", " ◈◈◈ ", "  ◈  "],
                ["  ◈  ", " ◈·◈ ", "  ◈  "]]
    if stage == AeonStage.ROOKIE:
        return [["  ◈  ", " ◈◉◈ ", "  ◈  "],
                ["  ◈  ", " ◈◎◈ ", "  ◈  "]]
    if stage == AeonStage.CHAMPION:
        return [
            ["  ⊕━━━⊕  ",
             " ╱ ◎◉◎ ╲ ",
             " ⊕ ╔═╗ ⊕ ",
             "   ╚═╝   ",
             "  ⊕━━━⊕  "],
            ["  ⊕─── ⊕ ",
             " ╱ ◉◎◉ ╲ ",
             " ⊕ ╔═╗ ⊕ ",
             "   ╚═╝   ",
             "  ⊕─── ⊕ "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            ["◈━━━━━━━◈ ",
             "╱ ◈ ◎◉◎ ◈╲",
             "◈ ╔══════╗ ◈",
             "╲ ◈ ◎◉◎ ◈╱",
             "◈━━━━━━━◈ "],
            ["◈───────◈ ",
             "╱ ◈ ◉◎◉ ◈╲",
             "◈ ╔══════╗ ◈",
             "╲ ◈ ◉◎◉ ◈╱",
             "◈───────◈ "],
        ]
    return [
        ["◈━━━━━━━━━◈",
         "╱◈ ◎◉◎◉◎ ◈╲",
         "◈ ╔════════╗ ◈",
         "╲◈ ◎◉◎◉◎ ◈╱",
         "◈━━━━━━━━━◈"],
        ["◈─────────◈",
         "╱◈ ◉◎◉◎◉ ◈╲",
         "◈ ╔════════╗ ◈",
         "╲◈ ◉◎◉◎◉ ◈╱",
         "◈─────────◈"],
    ]


def _frames_forja(stage: AeonStage, seed: int) -> list[list[str]]:
    if stage in (AeonStage.HUEVO, AeonStage.FRESH, AeonStage.ROOKIE):
        return [["◉─◉", "│F│", "◉─◉"],
                ["◉━◉", "│F│", "◉━◉"]]
    if stage == AeonStage.CHAMPION:
        return [
            [" ◉━◈━◉ ",
             " │╔═╗│ ",
             "◉─╣F ╠─◉",
             " │╚═╝│ ",
             " ◉━◈━◉ "],
            [" ◉─◈─◉ ",
             " │╔═╗│ ",
             "◉━╣F ╠━◉",
             " │╚═╝│ ",
             " ◉─◈─◉ "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            ["◉━◈━◉━◈━◉",
             "║ ╔══════╗ ║",
             "╠══╣◈  F◈╠══╣",
             "║ ╚══════╝ ║",
             "◉━◈━◉━◈━◉"],
            ["◉─◈─◉─◈─◉",
             "║ ╔══════╗ ║",
             "╠──╣◈  F◈╠──╣",
             "║ ╚══════╝ ║",
             "◉─◈─◉─◈─◉"],
        ]
    return [
        ["◉━━◈━━◉━━◈━━◉",
         "║  ╔═══════╗  ║",
         "╠══╣ ◈  F  ◈╠══╣",
         "║  ╚═══════╝  ║",
         "◉━━◈━━◉━━◈━━◉"],
        ["◉──◈──◉──◈──◉",
         "║  ╔═══════╗  ║",
         "╠──╣ ◈  F  ◈╠──╣",
         "║  ╚═══════╝  ║",
         "◉──◈──◉──◈──◉"],
    ]


def _frames_marea(stage: AeonStage, seed: int) -> list[list[str]]:
    if stage in (AeonStage.HUEVO, AeonStage.FRESH, AeonStage.ROOKIE):
        return [["∿∿∿", "∿M∿", "∿∿∿"],
                ["≋≋≋", "≋M≋", "≋≋≋"]]
    if stage == AeonStage.CHAMPION:
        return [
            [" ≋≋≋≋≋ ",
             "∿╔═════╗∿",
             "≋║∿M∿∿ ║≋",
             "∿╚═════╝∿",
             " ≋≋≋≋≋ "],
            [" ∿∿∿∿∿ ",
             "≋╔═════╗≋",
             "∿║≋M≋≋ ║∿",
             "≋╚═════╝≋",
             " ∿∿∿∿∿ "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            ["≋≋≋≋≋≋≋≋≋",
             "∿╔═══════╗∿",
             "≋║∿∿M∿∿∿ ║≋",
             "∿╚═══════╝∿",
             "≋≋≋≋≋≋≋≋≋"],
            ["∿∿∿∿∿∿∿∿∿",
             "≋╔═══════╗≋",
             "∿║≋≋M≋≋≋ ║∿",
             "≋╚═══════╝≋",
             "∿∿∿∿∿∿∿∿∿"],
        ]
    return [
        ["≋≋≋≋≋≋≋≋≋≋≋",
         "∿╔═══════════╗∿",
         "≋║ ∿∿M∿∿∿∿  ║≋",
         "∿╚═══════════╝∿",
         "≋≋≋≋≋≋≋≋≋≋≋"],
        ["∿∿∿∿∿∿∿∿∿∿∿",
         "≋╔═══════════╗≋",
         "∿║ ≋≋M≋≋≋≋  ║∿",
         "≋╚═══════════╝≋",
         "∿∿∿∿∿∿∿∿∿∿∿"],
    ]


def _frames_raiz(stage: AeonStage, seed: int) -> list[list[str]]:
    star = ["✦", "·", "✧"][seed % 3]
    if stage in (AeonStage.HUEVO, AeonStage.FRESH, AeonStage.ROOKIE):
        return [
            [f"  {star}  ", "  │  ", " ═╧═ "],
            [f"  {star}  ", "  │  ", " ─╧─ "],
        ]
    if stage == AeonStage.CHAMPION:
        return [
            [f"    {star}    ",
             "   ╱│╲   ",
             "  ╱ │ ╲  ",
             " ◇  │  ◇ ",
             "   ═╧═   "],
            [f"    {star}    ",
             "   ╱│╲   ",
             "  ╱ │ ╲  ",
             " ◇  │  ◇ ",
             "   ─╧─   "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            [f"{star}   {star}   {star}",
             "╱│╲ ╱│╲ ╱│╲",
             "╱ ╔═════╗ ╲",
             "◇ ║ R ◈ ║ ◇",
             "  ╚═════╝  ",
             "  ═══╧═══  "],
            [f"·   {star}   ·",
             "╱│╲ ╱│╲ ╱│╲",
             "╱ ╔═════╗ ╲",
             "◇ ║ R ◈ ║ ◇",
             "  ╚═════╝  ",
             "  ───╧───  "],
        ]
    return [
        [f"{star}  {star}  {star}  {star}",
         "╱│╲╱│╲╱│╲╱│╲",
         "╱ ╔═══════╗ ╲",
         "◇ ║ ◈ R ◈ ║ ◇",
         "  ╚═══════╝  ",
         " ═════╧═════ "],
        [f"·  {star}  {star}  ·",
         "╱│╲╱│╲╱│╲╱│╲",
         "╱ ╔═══════╗ ╲",
         "◇ ║ ◈ R ◈ ║ ◇",
         "  ╚═══════╝  ",
         " ─────╧───── "],
    ]


def _frames_vacio(stage: AeonStage, seed: int) -> list[list[str]]:
    # Stars appear/disappear asynchronously
    if stage in (AeonStage.HUEVO, AeonStage.FRESH, AeonStage.ROOKIE):
        return [
            ["· · ·", "·(◉)·", "· · ·"],
            ["· ★ ·", "·(◎)·", "· · ·"],
        ]
    if stage == AeonStage.CHAMPION:
        return [
            [" · ★ · ",
             "·╔════╗·",
             "·║◉◎◉ ║·",
             "·╚════╝·",
             " · · · "],
            [" · · · ",
             "·╔════╗·",
             "·║◎◉◎ ║·",
             "·╚════╝·",
             " · ★ · "],
        ]
    if stage == AeonStage.ULTIMATE:
        return [
            ["·  ·  ★  ·  ·",
             "·╔══════════╗·",
             "· ║·◉·◎·◉·◎·║ ·",
             "·╚══════════╝·",
             "·  ·  ·  ★  ·"],
            ["·  ★  ·  ·  ·",
             "·╔══════════╗·",
             "· ║·◎·◉·◎·◉·║ ·",
             "·╚══════════╝·",
             "·  ·  ★  ·  ·"],
        ]
    return [
        ["·  ·  ★  ·  ·  ·",
         "·╔══════════════╗·",
         "· ║·◉·◎·◉·◎·◉·◎·║ ·",
         "·╚══════════════╝·",
         "·  ★  ·  ·  ·  ★"],
        ["·  ★  ·  ★  ·  ·",
         "·╔══════════════╗·",
         "· ║·◎·◉·◎·◉·◎·◉·║ ·",
         "·╚══════════════╝·",
         "·  ·  ★  ·  ★  ·"],
    ]


def _frames_unknown(stage: AeonStage, seed: int) -> list[list[str]]:
    return [
        ["  ?  ", " ╔═╗ ", " ║?║ ", " ╚═╝ ", "  ?  "],
        ["  ·  ", " ╔═╗ ", " ║·║ ", " ╚═╝ ", "  ·  "],
    ]


_FRAME_BUILDERS = {
    AeonArchetype.LLAMA:   _frames_llama,
    AeonArchetype.ORACULO: _frames_oraculo,
    AeonArchetype.FORJA:   _frames_forja,
    AeonArchetype.MAREA:   _frames_marea,
    AeonArchetype.RAIZ:    _frames_raiz,
    AeonArchetype.VACIO:   _frames_vacio,
    AeonArchetype.UNKNOWN: _frames_unknown,
}


# ── Profile loading ────────────────────────────────────────────────────────────

@dataclass
class AeonProfile:
    name: str = "Exodia"
    archetype: AeonArchetype = AeonArchetype.UNKNOWN
    init_at: str = ""
    vault_notes: int = 0
    memory_count: int = 0
    ledger_count: int = 0

    @classmethod
    def load(cls) -> "AeonProfile":
        data: dict = {}
        if AEON_PROFILE_PATH.exists():
            try:
                data = json.loads(AEON_PROFILE_PATH.read_text())
            except Exception:
                pass
        archetype_str = data.get("archetype", "unknown")
        try:
            archetype = AeonArchetype(archetype_str)
        except ValueError:
            archetype = AeonArchetype.UNKNOWN

        profile = cls(
            name=data.get("name", "Exodia"),
            archetype=archetype,
            init_at=data.get("init_at", ""),
            vault_notes=data.get("vault_notes", 0),
            memory_count=data.get("memory_count", 0),
            ledger_count=data.get("ledger_count", 0),
        )
        profile._enrich_from_db()
        return profile

    def save(self) -> None:
        AEON_HOME.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "archetype": self.archetype.value,
            "init_at": self.init_at,
            "vault_notes": self.vault_notes,
            "memory_count": self.memory_count,
            "ledger_count": self.ledger_count,
        }
        AEON_PROFILE_PATH.write_text(json.dumps(data, indent=2))

    def _enrich_from_db(self) -> None:
        if not EPISODIC_DB.exists():
            return
        try:
            import sqlite3
            conn = sqlite3.connect(EPISODIC_DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memories")
            self.memory_count = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass

    @property
    def days_alive(self) -> int:
        if not self.init_at:
            return 0
        from datetime import datetime, timezone
        try:
            born = datetime.fromisoformat(self.init_at)
            now = datetime.now(timezone.utc)
            if born.tzinfo is None:
                from datetime import timezone as tz
                born = born.replace(tzinfo=tz.utc)
            return max(0, (now - born).days)
        except Exception:
            return 0

    @property
    def stage(self) -> AeonStage:
        d = self.days_alive
        m = self.memory_count
        if d == 0:
            return AeonStage.HUEVO
        if d <= 3:
            return AeonStage.FRESH
        if d <= 30 and m < 100:
            return AeonStage.ROOKIE
        if d <= 180 and m < 1000:
            return AeonStage.CHAMPION
        if d <= 365 and m < 10000:
            return AeonStage.ULTIMATE
        return AeonStage.MEGA

    @property
    def seed(self) -> int:
        return hash(self.name + self.init_at) & 0xFFFFFFFF

    @property
    def stage_label(self) -> str:
        labels = {
            AeonStage.HUEVO:     "◇ HUEVO",
            AeonStage.FRESH:     "◈ FRESH",
            AeonStage.ROOKIE:    "▷ ROOKIE",
            AeonStage.CHAMPION:  "◆ CHAMPION",
            AeonStage.ULTIMATE:  "❖ ULTIMATE",
            AeonStage.MEGA:      "✦ MEGA",
            AeonStage.SOVEREIGN: "⟡ SOVEREIGN",
        }
        return labels.get(self.stage, self.stage.value)

    @property
    def primary_color(self) -> str:
        return ARCHETYPE_COLORS[self.archetype][0]

    @property
    def accent_color(self) -> str:
        return ARCHETYPE_COLORS[self.archetype][1]

    @property
    def archetype_name(self) -> str:
        return ARCHETYPE_LABELS[self.archetype][0]

    @property
    def archetype_tagline(self) -> str:
        return ARCHETYPE_LABELS[self.archetype][1]


# ── Sigil rendering ────────────────────────────────────────────────────────────

def _get_frames(profile: AeonProfile) -> list[list[str]]:
    builder = _FRAME_BUILDERS.get(profile.archetype, _frames_unknown)
    return builder(profile.stage, profile.seed)


def _breathing_delay(t: float, state: AeonState) -> float:
    """e^sin breathing rhythm. Returns frame delay in seconds."""
    if state == AeonState.PROCESSING:
        return 0.18
    if state == AeonState.SLEEPING:
        return 2.0
    # Idle: e^sin(t) normalized to [0.4, 1.2] seconds
    raw = math.exp(math.sin(t * 0.8))  # [e^-1, e^1] ≈ [0.37, 2.72]
    return 0.3 + (raw - 0.37) / (2.72 - 0.37) * 0.9


def _render_frame(
    profile: AeonProfile,
    frame_lines: list[str],
    state: AeonState,
    frame_idx: int,
) -> Panel:
    pc = profile.primary_color
    ac = profile.accent_color

    # Build sigil art with color
    art = Text()
    for i, line in enumerate(frame_lines):
        if i > 0:
            art.append("\n")
        art.append(line, style=pc)

    # State indicator
    state_marks = {
        AeonState.IDLE:       ("·", "dim"),
        AeonState.PROCESSING: ("◉", ac),
        AeonState.SLEEPING:   ("z", "dim"),
        AeonState.EVOLVING:   ("★", "bright_yellow"),
    }
    s_char, s_style = state_marks[state]

    # Stats block
    stats = Text()
    stats.append(f"\n{profile.name}\n", style=f"bold {pc}")
    stats.append("─" * max(len(profile.name), 16) + "\n", style="dim")
    stats.append(f"Etapa:    ", style="dim")
    stats.append(f"{profile.stage_label}\n", style=ac)
    stats.append(f"Arquetipo: ", style="dim")
    stats.append(f"{profile.archetype_name}\n", style=pc)
    stats.append(f"Días:     ", style="dim")
    stats.append(f"{profile.days_alive}\n", style="white")
    stats.append(f"Memorias: ", style="dim")
    stats.append(f"{profile.memory_count:,}\n", style="white")
    if profile.vault_notes:
        stats.append(f"Vault:    ", style="dim")
        stats.append(f"{profile.vault_notes:,} notas\n", style="white")
    if profile.ledger_count:
        stats.append(f"Ledger:   ", style="dim")
        stats.append(f"{profile.ledger_count} entradas\n", style="white")
    stats.append(f"\n⟡ {profile.archetype_tagline} ⟡", style=f"dim {ac}")

    # Combine art + stats side by side using a simple layout
    content = Text()
    art_lines = frame_lines
    stats_lines = stats.plain.split("\n")

    max_art_w = max(len(l) for l in art_lines)
    combined_lines = max(len(art_lines), len(stats_lines))

    for i in range(combined_lines):
        art_l = art_lines[i] if i < len(art_lines) else ""
        stat_l = stats_lines[i] if i < len(stats_lines) else ""
        pad = max_art_w - len(art_l)
        if i > 0:
            content.append("\n")
        content.append(art_l.ljust(max_art_w), style=pc)
        content.append("  ")
        # Apply basic style to stats
        if i == 1:  # name line
            content.append(stat_l, style=f"bold {pc}")
        elif stat_l.startswith("─"):
            content.append(stat_l, style="dim")
        elif "⟡" in stat_l:
            content.append(stat_l, style=f"dim {ac}")
        else:
            parts = stat_l.split(":", 1)
            if len(parts) == 2:
                content.append(parts[0] + ":", style="dim")
                content.append(parts[1], style="white")
            else:
                content.append(stat_l, style="white")

    border_color = pc if state != AeonState.SLEEPING else "dim"
    return Panel(
        content,
        title=f"[{ac}] ◈ AEON VIVO [{s_style}]{s_char}[/{s_style}] [/{ac}]",
        border_style=border_color,
        padding=(1, 2),
    )


def render_card(profile: AeonProfile) -> str:
    """Render exportable text card for sharing (like Digimon card)."""
    frames = _get_frames(profile)
    art = frames[0]
    max_w = max(len(l) for l in art)
    border = "═" * (max_w + 4)
    lines = [
        f"╔{border}╗",
        f"║  {'ZANA AEON':^{max_w}}  ║",
        f"╠{border}╣",
    ]
    for l in art:
        lines.append(f"║  {l:<{max_w}}  ║")
    lines += [
        f"╠{border}╣",
        f"║  {'Nombre: ' + profile.name:<{max_w}}  ║",
        f"║  {'Etapa:  ' + profile.stage_label:<{max_w}}  ║",
        f"║  {'Tipo:   ' + profile.archetype_name:<{max_w}}  ║",
        f"║  {'Días:   ' + str(profile.days_alive):<{max_w}}  ║",
        f"║  {'Memorias: ' + str(profile.memory_count):<{max_w}}  ║",
        f"╚{border}╝",
        f"  ⟡ {profile.archetype_tagline} ⟡",
        f"  pip install zana  ·  zana.vecanova.com",
    ]
    return "\n".join(lines)


def render_mini(profile: AeonProfile, state: AeonState = AeonState.IDLE) -> str:
    """5-char inline sigil for chat header."""
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
    state_pulse = {
        AeonState.IDLE:       "·",
        AeonState.PROCESSING: "◉",
        AeonState.SLEEPING:   "z",
        AeonState.EVOLVING:   "★",
    }
    core = archetype_mini.get(profile.archetype, "?")
    stage = stage_mini.get(profile.stage, "?")
    pulse = state_pulse.get(state, "·")
    return f"[{pulse}{core}{stage}]"


def animate(
    profile: AeonProfile,
    state: AeonState = AeonState.IDLE,
    duration: float | None = None,
    console: Console | None = None,
) -> None:
    """Run live animation. duration=None loops until Ctrl+C."""
    if console is None:
        from cli.tui.theme import console as default_console
        console = default_console

    frames = _get_frames(profile)
    t = 0.0
    start = time.monotonic()
    frame_idx = 0

    try:
        with Live(console=console, refresh_per_second=4) as live:
            while True:
                frame = frames[frame_idx % len(frames)]
                panel = _render_frame(profile, frame, state, frame_idx)
                live.update(panel)
                delay = _breathing_delay(t, state)
                time.sleep(delay)
                t += delay
                frame_idx += 1
                if duration and (time.monotonic() - start) >= duration:
                    break
    except KeyboardInterrupt:
        pass
