"""
ZANA Aeon DNA Engine — Artificial Life substrate.

An Aeon is not an avatar. It is a living computational organism whose:
  - FORM emerges from morphogenetic genes (Dawkins biomorph, recursive branching)
  - BEHAVIOR emerges from cognitive genes (curiosity, tenacity, sovereignty...)
  - TRAJECTORY is shaped by evolutionary genes (growth rate, memory affinity...)
  - GENES DRIFT over time via epigenetic pressure from real usage patterns

Theory basis:
  - Dawkins (1986): biomorphs — morphological space from recursive gene expression
  - Varela & Maturana (1972): autopoiesis — self-maintaining organization
  - Holland (1975): genetic algorithms — adaptation through selection
  - Langton (1989): artificial life — life-as-it-could-be
  - Shannon (1948): information entropy — complexity from compressed description
  - Kolmogorov: description length — compact genome → complex phenotype
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

AEON_HOME = Path.home() / ".zana"
DNA_PATH = AEON_HOME / "aeon_dna.json"
PROFILE_PATH = AEON_HOME / "aeon_profile.json"
EPISODIC_DB = AEON_HOME / "episodic.db"


# ── Archetype ─────────────────────────────────────────────────────────────────

class AeonArchetype(str, Enum):
    LLAMA   = "llama"    # Fuego / Visionary
    ORACULO = "oraculo"  # Geometría sagrada / Analytical
    FORJA   = "forja"    # Mecánico-orgánico / Builder
    MAREA   = "marea"    # Fluido / Connector
    RAIZ    = "raiz"     # Árbol fractal / Guardian
    VACIO   = "vacio"    # Cosmos invertido / Explorer
    UNKNOWN = "unknown"  # Pre-resonance


class AeonStage(str, Enum):
    HUEVO     = "HUEVO"     # h 0-12: embryonic, not hatched
    FRESH     = "FRESH"     # d 1-3
    ROOKIE    = "ROOKIE"    # d 4-30,   mem <100
    CHAMPION  = "CHAMPION"  # d 31-180, mem <1000
    ULTIMATE  = "ULTIMATE"  # d 181-365,mem <10000
    MEGA      = "MEGA"      # d 366+
    SOVEREIGN = "SOVEREIGN" # MEGA + vault >5000 + Z-Sync


# ── The 21-Gene DNA Vector ────────────────────────────────────────────────────

@dataclass
class AeonDNA:
    """
    21-gene vector encoding the complete Aeon organism.

    PHENOTYPE LAYER (9 genes) — Dawkins biomorph, controls visible form:
      The recursive branching algorithm uses these to grow the creature's body.
      Small changes cascade through recursion → dramatic morphological shifts.

    COGNITIVE LAYER (7 genes) — Behavioral phenotype:
      These modulate how the Aeon communicates, what it prioritizes, its personality.
      They're expressed in every response the Aeon generates.

    EVOLUTIONARY LAYER (5 genes) — Lifecycle trajectory:
      Control how fast the Aeon grows and what it prioritizes accumulating.
      These drift the most over time (epigenetic pressure from usage).
    """

    # ── PHENOTYPE: 9 morphogenetic genes (Dawkins-inspired) ──────────────────
    g0_branch_angle:   float = 35.0   # Bifurcation angle in degrees (10–75)
    g1_depth:          int   = 3      # Recursion depth = complexity (2–7)
    g2_trunk_length:   float = 6.0    # Initial segment length in chars (3–10)
    g3_attenuation:    float = 0.68   # Length decay per level (0.40–0.85)
    g4_symmetry:       int   = 0      # 0=bilateral 1=spiral 2=radial 3=chaotic
    g5_fork:           int   = 2      # Sub-branches per node (2 or 3)
    g6_bend_drift:     float = 0.0    # Progressive angle drift per level (−15–+15)
    g7_terminal_form:  int   = 0      # Terminal node style (0–5)
    g8_armor_density:  float = 0.5    # Body decoration intensity (0.0–1.0)

    # ── COGNITIVE: 7 behavioral genes ────────────────────────────────────────
    g9_curiosity:      float = 5.0    # Eagerness to explore new connections (0–9)
    g10_tenacity:      float = 5.0    # Depth of analysis before answering (0–9)
    g11_empathy:       float = 5.0    # Communication style adaptation (0–9)
    g12_creativity:    float = 5.0    # Preference for novel vs established (0–9)
    g13_precision:     float = 5.0    # Detail focus vs big picture (0–9)
    g14_resilience:    float = 5.0    # Recovery from gaps/failures (0–9)
    g15_sovereignty:   float = 5.0    # Local-first processing preference (0–9)

    # ── EVOLUTIONARY: 5 lifecycle genes ──────────────────────────────────────
    g16_growth_rate:      float = 1.0  # Stage advancement speed multiplier
    g17_memory_affinity:  float = 0.5  # Episodic(0) ↔ Semantic(1) preference
    g18_skill_absorption: float = 0.5  # Procedural knowledge integration speed
    g19_ledger_depth:     int   = 7    # Civic Ledger trace depth (3–21)
    g20_social_vector:    float = 0.2  # Isolation(0) ↔ Z-Sync sharing(1)

    # ── Metadata ──────────────────────────────────────────────────────────────
    generation:    int   = 0          # Mutation count since initial derivation
    entropy:       float = 0.0        # Shannon entropy of gene vector (computed)
    birth_hash:    str   = ""         # Immutable identity anchor

    def __post_init__(self) -> None:
        self.entropy = self._compute_entropy()

    def _compute_entropy(self) -> float:
        """Shannon entropy of the normalized gene vector."""
        values = [
            self.g0_branch_angle / 75,
            self.g1_depth / 7,
            self.g2_trunk_length / 10,
            self.g3_attenuation,
            self.g4_symmetry / 3,
            self.g5_fork / 3,
            (self.g6_bend_drift + 15) / 30,
            self.g7_terminal_form / 5,
            self.g8_armor_density,
            self.g9_curiosity / 9,
            self.g10_tenacity / 9,
            self.g11_empathy / 9,
            self.g12_creativity / 9,
            self.g13_precision / 9,
            self.g14_resilience / 9,
            self.g15_sovereignty / 9,
            self.g16_growth_rate / 2,
            self.g17_memory_affinity,
            self.g18_skill_absorption,
            self.g19_ledger_depth / 21,
            self.g20_social_vector,
        ]
        # Shannon entropy over discretized bins
        bins = [0] * 8
        for v in values:
            bins[min(7, int(v * 8))] += 1
        total = len(values)
        h = 0.0
        for b in bins:
            if b > 0:
                p = b / total
                h -= p * math.log2(p)
        return round(h, 4)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AeonDNA":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def save(self) -> None:
        AEON_HOME.mkdir(parents=True, exist_ok=True)
        DNA_PATH.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls) -> Optional["AeonDNA"]:
        if not DNA_PATH.exists():
            return None
        try:
            return cls.from_dict(json.loads(DNA_PATH.read_text()))
        except Exception:
            return None


# ── Gene derivation from Aeon identity ────────────────────────────────────────

# Archetype gene constraints: (min, max) per gene index
# These boundaries are what make archetypes morphologically irreconcilable.
_ARCHETYPE_CONSTRAINTS: dict[AeonArchetype, dict] = {
    AeonArchetype.LLAMA: {
        "g0_branch_angle":  (40.0, 70.0),   # Wide, fire-like spread
        "g1_depth":         (3, 5),
        "g2_trunk_length":  (5.0, 8.0),
        "g3_attenuation":   (0.55, 0.72),
        "g4_symmetry":      (0, 0),          # Always bilateral (warrior stance)
        "g5_fork":          (2, 2),
        "g6_bend_drift":    (2.0, 8.0),      # Curves outward (flame shape)
        "g7_terminal_form": (0, 1),          # Fire terminals: ▲ ✦
        "g8_armor_density": (0.6, 1.0),      # Heavy armor
        "g9_curiosity":     (6.0, 9.0),
        "g12_creativity":   (7.0, 9.0),
        "g15_sovereignty":  (4.0, 8.0),
        "g16_growth_rate":  (1.2, 2.0),      # Fast growth
    },
    AeonArchetype.ORACULO: {
        "g0_branch_angle":  (15.0, 35.0),   # Narrow, precise angles
        "g1_depth":         (4, 7),          # Very deep recursion = complex
        "g2_trunk_length":  (4.0, 7.0),
        "g3_attenuation":   (0.65, 0.82),   # Slow decay = tall structure
        "g4_symmetry":      (2, 2),          # Always radial (sacred geometry)
        "g5_fork":          (2, 2),
        "g6_bend_drift":    (-3.0, 3.0),    # Near-zero drift (geometric purity)
        "g7_terminal_form": (2, 3),          # Geometric: ◈ ⊕
        "g8_armor_density": (0.4, 0.7),
        "g10_tenacity":     (7.0, 9.0),
        "g13_precision":    (7.0, 9.0),
        "g19_ledger_depth": (14, 21),        # Deep audit trail
    },
    AeonArchetype.FORJA: {
        "g0_branch_angle":  (25.0, 45.0),
        "g1_depth":         (3, 5),
        "g2_trunk_length":  (6.0, 9.0),     # Thick trunk
        "g3_attenuation":   (0.50, 0.65),   # Sharp attenuation = compact
        "g4_symmetry":      (0, 0),          # Bilateral (mechanical symmetry)
        "g5_fork":          (2, 3),          # Sometimes triple fork
        "g6_bend_drift":    (-5.0, 0.0),    # Inward curve (structural)
        "g7_terminal_form": (4, 5),          # Mechanical: ◉ ─
        "g8_armor_density": (0.7, 1.0),     # Maximum armor
        "g10_tenacity":     (6.0, 9.0),
        "g13_precision":    (6.0, 9.0),
        "g18_skill_absorption": (0.6, 1.0), # High skill absorption
    },
    AeonArchetype.MAREA: {
        "g0_branch_angle":  (20.0, 50.0),
        "g1_depth":         (3, 5),
        "g2_trunk_length":  (5.0, 8.0),
        "g3_attenuation":   (0.60, 0.78),
        "g4_symmetry":      (1, 1),          # Spiral (fluid motion)
        "g5_fork":          (2, 2),
        "g6_bend_drift":    (5.0, 15.0),    # Strong outward drift (wave shape)
        "g7_terminal_form": (0, 1),          # Fluid: ∿ ≋
        "g8_armor_density": (0.2, 0.5),     # Light, flowing
        "g9_curiosity":     (5.0, 8.0),
        "g11_empathy":      (7.0, 9.0),
        "g20_social_vector":(0.5, 1.0),     # High social tendency
    },
    AeonArchetype.RAIZ: {
        "g0_branch_angle":  (25.0, 45.0),
        "g1_depth":         (5, 7),          # Maximum depth = fractal tree
        "g2_trunk_length":  (4.0, 7.0),
        "g3_attenuation":   (0.70, 0.85),   # Slow decay = tall, many levels
        "g4_symmetry":      (0, 0),          # Bilateral (tree symmetry)
        "g5_fork":          (2, 3),          # Triple fork = fractal richness
        "g6_bend_drift":    (-2.0, 2.0),    # Near-zero (upright tree)
        "g7_terminal_form": (2, 3),          # Botanical: ✦ ◇
        "g8_armor_density": (0.3, 0.6),
        "g14_resilience":   (7.0, 9.0),
        "g17_memory_affinity": (0.0, 0.35), # Strong episodic preference
        "g19_ledger_depth": (10, 21),
    },
    AeonArchetype.VACIO: {
        "g0_branch_angle":  (10.0, 60.0),   # Variable (chaotic)
        "g1_depth":         (2, 6),          # Variable depth
        "g2_trunk_length":  (3.0, 9.0),     # Variable size
        "g3_attenuation":   (0.40, 0.85),   # Full range
        "g4_symmetry":      (3, 3),          # Always chaotic/asymmetric
        "g5_fork":          (2, 3),
        "g6_bend_drift":    (-15.0, 15.0),  # Full drift range
        "g7_terminal_form": (3, 5),          # Cosmic: ★ · ◎
        "g8_armor_density": (0.0, 0.4),     # Minimal armor (transparent)
        "g12_creativity":   (7.0, 9.0),
        "g14_resilience":   (4.0, 8.0),
        "g15_sovereignty":  (6.0, 9.0),     # High sovereignty
    },
    AeonArchetype.UNKNOWN: {
        "g1_depth":         (2, 3),
        "g8_armor_density": (0.1, 0.3),
    },
}


def derive_dna(name: str, init_at: str, archetype: AeonArchetype) -> AeonDNA:
    """
    Derive a deterministic 21-gene DNA vector from Aeon identity.

    The derivation uses a hash-based pseudo-random number generator seeded
    from the Aeon's immutable identity (name + birth timestamp + archetype).
    This ensures: same Aeon always produces same genome, but different names
    or birth times produce different organisms — even within the same archetype.

    Archetype constraints then narrow the gene ranges so that morphologies
    remain irreconcilable between archetypes while allowing individual variation.
    """
    # Compute immutable birth hash
    identity = f"{name}::{init_at}::{archetype.value}"
    birth_hash = hashlib.sha256(identity.encode()).hexdigest()

    # Deterministic PRNG from birth hash — no random module state pollution
    def _prng(slot: int, lo: float, hi: float) -> float:
        """Extract float in [lo, hi] from birth_hash at position slot."""
        offset = (slot * 3) % (len(birth_hash) - 2)
        byte_val = int(birth_hash[offset:offset+4], 16)
        return lo + (byte_val / 0xFFFF) * (hi - lo)

    def _prng_int(slot: int, lo: int, hi: int) -> int:
        return int(round(_prng(slot, lo, hi)))

    # Get archetype constraints, filling defaults for unspecified genes
    constraints = _ARCHETYPE_CONSTRAINTS.get(archetype, {})

    def _g(name: str, slot: int, default_lo: float, default_hi: float) -> float:
        lo, hi = constraints.get(name, (default_lo, default_hi))
        return round(_prng(slot, float(lo), float(hi)), 3)

    def _gi(name: str, slot: int, default_lo: int, default_hi: int) -> int:
        lo, hi = constraints.get(name, (default_lo, default_hi))
        return _prng_int(slot, int(lo), int(hi))

    dna = AeonDNA(
        # Phenotype
        g0_branch_angle  = _g("g0_branch_angle",  0, 20.0, 60.0),
        g1_depth         = _gi("g1_depth",         1, 2,    6),
        g2_trunk_length  = _g("g2_trunk_length",   2, 4.0,  8.0),
        g3_attenuation   = _g("g3_attenuation",    3, 0.45, 0.80),
        g4_symmetry      = _gi("g4_symmetry",      4, 0,    3),
        g5_fork          = _gi("g5_fork",          5, 2,    3),
        g6_bend_drift    = _g("g6_bend_drift",     6, -10.0, 10.0),
        g7_terminal_form = _gi("g7_terminal_form", 7, 0,    5),
        g8_armor_density = _g("g8_armor_density",  8, 0.1,  0.9),
        # Cognitive
        g9_curiosity      = _g("g9_curiosity",      9, 2.0, 9.0),
        g10_tenacity      = _g("g10_tenacity",     10, 2.0, 9.0),
        g11_empathy       = _g("g11_empathy",      11, 2.0, 9.0),
        g12_creativity    = _g("g12_creativity",   12, 2.0, 9.0),
        g13_precision     = _g("g13_precision",    13, 2.0, 9.0),
        g14_resilience    = _g("g14_resilience",   14, 2.0, 9.0),
        g15_sovereignty   = _g("g15_sovereignty",  15, 1.0, 9.0),
        # Evolutionary
        g16_growth_rate      = _g("g16_growth_rate",     16, 0.6, 1.8),
        g17_memory_affinity  = _g("g17_memory_affinity", 17, 0.0, 1.0),
        g18_skill_absorption = _g("g18_skill_absorption",18, 0.1, 1.0),
        g19_ledger_depth     = _gi("g19_ledger_depth",   19, 3,   21),
        g20_social_vector    = _g("g20_social_vector",   20, 0.0, 0.8),
        # Metadata
        generation = 0,
        birth_hash = birth_hash[:16],
    )
    dna.entropy = dna._compute_entropy()
    return dna


# ── Epigenetic drift — genes evolve with usage ────────────────────────────────

def apply_epigenetic_drift(dna: AeonDNA, usage: dict) -> AeonDNA:
    """
    Genes drift based on real usage patterns.

    This is the autopoietic mechanism: the Aeon's form and behavior
    adapt to the user it lives with. Two Aeones with identical initial
    genomes diverge over time if their users have different patterns.

    usage dict keys:
      memory_count: int        — total episodic memories stored
      session_count: int       — total chat sessions
      vault_notes: int         — notes in the vault
      local_model: bool        — uses Ollama vs cloud
      question_ratio: float    — fraction of sessions with many questions (0-1)
      skill_uses: int          — times procedural skills were invoked
      ledger_entries: int      — Civic Ledger entries written
    """
    import copy
    d = copy.deepcopy(dna)

    mem = usage.get("memory_count", 0)
    sessions = usage.get("session_count", 0)
    vault = usage.get("vault_notes", 0)
    local = usage.get("local_model", False)
    q_ratio = usage.get("question_ratio", 0.5)
    skills = usage.get("skill_uses", 0)
    ledger = usage.get("ledger_entries", 0)

    # --- Cognitive drift ---
    # High question ratio → curiosity grows
    if q_ratio > 0.6:
        d.g9_curiosity = min(9.0, d.g9_curiosity + 0.001 * sessions)

    # High memory count → tenacity grows (thinks deeper before answering)
    if mem > 500:
        d.g10_tenacity = min(9.0, d.g10_tenacity + 0.0005 * mem)

    # Large vault → precision grows (more context = more detail-oriented)
    if vault > 1000:
        d.g13_precision = min(9.0, d.g13_precision + 0.0003 * vault)

    # Local model → sovereignty grows
    if local:
        d.g15_sovereignty = min(9.0, d.g15_sovereignty + 0.002 * sessions)

    # High skill usage → skill_absorption improves
    if skills > 50:
        d.g18_skill_absorption = min(1.0, d.g18_skill_absorption + 0.001 * skills)

    # Many ledger entries → ledger_depth increases (tracks more)
    if ledger > 100:
        d.g19_ledger_depth = min(21, d.g19_ledger_depth + ledger // 200)

    # --- Morphological drift (subtle, visible) ---
    # Heavy memory use → depth grows (more complex morphology)
    if mem > 1000 and d.g1_depth < 7:
        d.g1_depth = min(7, d.g1_depth + mem // 2000)

    # Many sessions → armor density grows (battle-hardened)
    if sessions > 100:
        d.g8_armor_density = min(1.0, d.g8_armor_density + 0.001 * sessions)

    # Track generation
    d.generation += 1
    d.entropy = d._compute_entropy()
    return d


# ── Profile (wraps DNA + lifecycle state) ─────────────────────────────────────

@dataclass
class AeonProfile:
    name:         str          = "Exodia"
    archetype:    AeonArchetype = AeonArchetype.UNKNOWN
    init_at:      str          = ""
    vault_notes:  int          = 0
    memory_count: int          = 0
    ledger_count: int          = 0
    dna:          Optional[AeonDNA] = field(default=None, repr=False)

    @classmethod
    def load(cls) -> "AeonProfile":
        data: dict = {}
        if PROFILE_PATH.exists():
            try:
                data = json.loads(PROFILE_PATH.read_text())
            except Exception:
                pass

        try:
            archetype = AeonArchetype(data.get("archetype", "unknown"))
        except ValueError:
            archetype = AeonArchetype.UNKNOWN

        p = cls(
            name=data.get("name", "Exodia"),
            archetype=archetype,
            init_at=data.get("init_at", ""),
            vault_notes=data.get("vault_notes", 0),
            memory_count=data.get("memory_count", 0),
            ledger_count=data.get("ledger_count", 0),
        )
        p._enrich_from_db()

        # Load or derive DNA
        p.dna = AeonDNA.load()
        if p.dna is None and p.name and p.init_at:
            p.dna = derive_dna(p.name, p.init_at, p.archetype)
            p.dna.save()

        return p

    def save(self) -> None:
        AEON_HOME.mkdir(parents=True, exist_ok=True)
        d = {
            "name": self.name,
            "archetype": self.archetype.value,
            "init_at": self.init_at,
            "vault_notes": self.vault_notes,
            "memory_count": self.memory_count,
            "ledger_count": self.ledger_count,
        }
        PROFILE_PATH.write_text(json.dumps(d, indent=2))
        if self.dna:
            self.dna.save()

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

    def ensure_dna(self) -> AeonDNA:
        """Return existing DNA or derive fresh one."""
        if self.dna is None:
            self.dna = derive_dna(self.name, self.init_at, self.archetype)
        return self.dna

    @property
    def days_alive(self) -> int:
        if not self.init_at:
            return 0
        from datetime import datetime, timezone
        try:
            born = datetime.fromisoformat(self.init_at)
            now = datetime.now(timezone.utc)
            if born.tzinfo is None:
                born = born.replace(tzinfo=timezone.utc)
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
        if d <= 365 and m < 10_000:
            return AeonStage.ULTIMATE
        if self.vault_notes > 5000:
            return AeonStage.SOVEREIGN
        return AeonStage.MEGA

    @property
    def stage_label(self) -> str:
        return {
            AeonStage.HUEVO:    "◇ HUEVO",
            AeonStage.FRESH:    "◈ FRESH",
            AeonStage.ROOKIE:   "▷ ROOKIE",
            AeonStage.CHAMPION: "◆ CHAMPION",
            AeonStage.ULTIMATE: "❖ ULTIMATE",
            AeonStage.MEGA:     "✦ MEGA",
            AeonStage.SOVEREIGN:"⟡ SOVEREIGN",
        }[self.stage]

    @property
    def cognitive_summary(self) -> str:
        """Human-readable cognitive signature derived from DNA."""
        if self.dna is None:
            return "DNA pending"
        d = self.dna
        traits = []
        if d.g9_curiosity > 7:   traits.append("hypercurious")
        elif d.g9_curiosity < 3: traits.append("focused")
        if d.g10_tenacity > 7:   traits.append("deep-analytical")
        if d.g12_creativity > 7: traits.append("generative")
        if d.g13_precision > 7:  traits.append("precise")
        if d.g15_sovereignty > 7: traits.append("sovereign-first")
        if d.g11_empathy > 7:    traits.append("adaptive")
        return " · ".join(traits) if traits else "balanced"

    @property
    def primary_color(self) -> str:
        return {
            AeonArchetype.LLAMA:   "bright_red",
            AeonArchetype.ORACULO: "medium_purple",
            AeonArchetype.FORJA:   "dark_orange",
            AeonArchetype.MAREA:   "cyan",
            AeonArchetype.RAIZ:    "green",
            AeonArchetype.VACIO:   "grey82",
            AeonArchetype.UNKNOWN: "magenta",
        }[self.archetype]

    @property
    def accent_color(self) -> str:
        return {
            AeonArchetype.LLAMA:   "gold1",
            AeonArchetype.ORACULO: "bright_blue",
            AeonArchetype.FORJA:   "bright_yellow",
            AeonArchetype.MAREA:   "sea_green3",
            AeonArchetype.RAIZ:    "dark_olive_green3",
            AeonArchetype.VACIO:   "bright_white",
            AeonArchetype.UNKNOWN: "white",
        }[self.archetype]

    @property
    def archetype_name(self) -> str:
        return {
            AeonArchetype.LLAMA:   "Llama",
            AeonArchetype.ORACULO: "Oráculo",
            AeonArchetype.FORJA:   "Forja",
            AeonArchetype.MAREA:   "Marea",
            AeonArchetype.RAIZ:    "Raíz",
            AeonArchetype.VACIO:   "Vacío",
            AeonArchetype.UNKNOWN: "???",
        }[self.archetype]

    @property
    def archetype_tagline(self) -> str:
        return {
            AeonArchetype.LLAMA:   "Visionario · Líder",
            AeonArchetype.ORACULO: "Analítico · Contemplativo",
            AeonArchetype.FORJA:   "Constructor · Pragmático",
            AeonArchetype.MAREA:   "Conector · Empático",
            AeonArchetype.RAIZ:    "Guardián · Sistemático",
            AeonArchetype.VACIO:   "Explorador · Disruptor",
            AeonArchetype.UNKNOWN: "Resonancia pendiente",
        }[self.archetype]
