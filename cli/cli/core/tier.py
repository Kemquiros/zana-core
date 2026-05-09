"""
Tier System — ZANA installation depth detector.

SEED    → ZSM only, no LLM key configured
SPROUT  → LLM configured, gateway not active
GROVE   → LLM + gateway active (Docker running)
FOREST  → Grove + satellite active (bot running)
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


class Tier(Enum):
    SEED = "seed"
    SPROUT = "sprout"
    GROVE = "grove"
    FOREST = "forest"


TIER_PROGRESS: dict[Tier, int] = {
    Tier.SEED: 1,
    Tier.SPROUT: 2,
    Tier.GROVE: 3,
    Tier.FOREST: 4,
}

_LLM_KEYS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OLLAMA_BASE_URL",
]

_PLACEHOLDER_VALUES = {
    "",
    "your_key_here",
    "sk-...",
    "AIza...",
    "gsk_...",
    "sk-ant-...",
    "change_me_strong_password",
}


def _has_llm_key() -> bool:
    """Check if at least one LLM provider key is configured."""
    for k in _LLM_KEYS:
        val = os.environ.get(k, "").strip()
        if val and val not in _PLACEHOLDER_VALUES:
            return True

    env_file = Path.home() / ".zana" / ".env"
    if not env_file.exists():
        return False

    try:
        content = env_file.read_text(encoding="utf-8")
    except Exception:
        return False

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.strip() in _LLM_KEYS:
            v = val.strip()
            if v and v not in _PLACEHOLDER_VALUES:
                return True
    return False


def _is_satellite_running() -> bool:
    """Check if satellite process is running via PID file."""
    pid_file = Path.home() / ".zana" / "satellite.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def _is_gateway_active() -> bool:
    """Quick non-blocking check if Gateway is responding."""
    try:
        import socket

        with socket.create_connection(("localhost", 54446), timeout=0.8):
            return True
    except Exception:
        return False


def detect_tier() -> Tier:
    """
    Detect current tier based on installed config state.
    Non-blocking: all probes have short timeouts.
    """
    if not _has_llm_key():
        return Tier.SEED

    if _is_satellite_running():
        return Tier.FOREST

    if _is_gateway_active():
        return Tier.GROVE

    return Tier.SPROUT


def tier_label(tier: Tier, lang: str = "es") -> str:
    from cli.core.i18n import t

    return t(f"tier.{tier.value}.name", lang=lang)


def tier_desc(tier: Tier, lang: str = "es") -> str:
    from cli.core.i18n import t

    return t(f"tier.{tier.value}.desc", lang=lang)


def tier_next_action(tier: Tier, lang: str = "es") -> str:
    from cli.core.i18n import t

    return t(f"tier.{tier.value}.next", lang=lang)


def tier_capabilities_text(tier: Tier, lang: str = "es") -> str:
    from cli.core.i18n import t

    return t(f"tier.{tier.value}.caps", lang=lang)


def tier_locked_text(tier: Tier, lang: str = "es") -> str:
    from cli.core.i18n import t

    return t(f"tier.{tier.value}.locked", lang=lang)


def tier_capabilities(tier: Tier) -> dict[str, bool]:
    """Return capability map for the given tier."""
    base = {
        "zsm": True,
        "reminders": True,
        "calculator": True,
        "home_economy": True,
        "aeon_dna": True,
        "llm_chat": False,
        "natural_reasoning": False,
        "persistent_memory": False,
        "semantic_vault": False,
        "satellite": False,
        "multi_user": False,
    }
    if tier in (Tier.SPROUT, Tier.GROVE, Tier.FOREST):
        base["llm_chat"] = True
        base["natural_reasoning"] = True
    if tier in (Tier.GROVE, Tier.FOREST):
        base["persistent_memory"] = True
        base["semantic_vault"] = True
    if tier == Tier.FOREST:
        base["satellite"] = True
        base["multi_user"] = True
    return base


def tier_progress_bar(tier: Tier) -> str:
    n = TIER_PROGRESS[tier]
    return "▓" * n + "░" * (4 - n)
