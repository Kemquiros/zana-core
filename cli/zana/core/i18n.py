"""
i18n — ZANA Internationalization Engine.

Simple dict-based translation system.
Fallback chain: configured_lang → "en" → key (never raises).
Locale files: cli/locales/{lang}.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent.parent / "locales"
_SUPPORTED = {"es", "en", "pt", "fr", "it", "de"}

_cache: dict[str, dict] = {}
_active_lang: str = "es"


def _load_file(lang: str) -> dict:
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_loaded(lang: str) -> dict:
    if lang not in _cache:
        _cache[lang] = _load_file(lang)
    return _cache[lang]


def _detect_lang() -> str:
    """Read ZANA_LANG from ~/.zana/.env or os.environ."""
    env_val = os.environ.get("ZANA_LANG", "").strip().lower()
    if env_val in _SUPPORTED:
        return env_val
    env_file = Path.home() / ".zana" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ZANA_LANG="):
                val = line.split("=", 1)[1].strip().lower()
                if val in _SUPPORTED:
                    return val
    return "es"


def get_lang() -> str:
    return _active_lang


def set_lang(lang: str) -> None:
    global _active_lang
    _active_lang = lang if lang in _SUPPORTED else "es"


def init_lang() -> str:
    """Detect and set active language from environment. Call once at startup."""
    lang = _detect_lang()
    set_lang(lang)
    return lang


def available_langs() -> list[str]:
    return sorted(_SUPPORTED)


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """
    Translate key to active language.

    Fallback chain: lang → "en" → key literal.
    Supports {variable} interpolation via kwargs.
    """
    active = lang or _active_lang
    locales = _ensure_loaded(active)
    text = locales.get(key)

    if text is None and active != "en":
        en_locales = _ensure_loaded("en")
        text = en_locales.get(key)

    if text is None:
        text = key

    if kwargs:
        import contextlib

        with contextlib.suppress(KeyError, ValueError):
            text = text.format(**kwargs)

    return text


# Initialize on import
_active_lang = _detect_lang()
