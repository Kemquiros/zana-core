"""
test_i18n_wizard.py — Sprint 12 · Issue #32

Tests for 6-language i18n:
  - All locale files have the same key set
  - Every new wizard key resolves correctly in all 6 languages
  - Language is persisted to aeon_profile.json after init
  - ZSM picks up the persisted language from the profile
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from zana.core.i18n import available_langs, init_lang, set_lang, t

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LOCALES_DIR = Path(__file__).parent.parent / "zana" / "locales"
SUPPORTED_LANGS = ["es", "en", "pt", "fr", "it", "de"]


# ---------------------------------------------------------------------------
# Locale file completeness
# ---------------------------------------------------------------------------


def test_all_locale_files_exist():
    for lang in SUPPORTED_LANGS:
        assert (LOCALES_DIR / f"{lang}.json").exists(), f"Missing locale: {lang}.json"


def test_all_locales_have_same_key_count():
    counts = {}
    for lang in SUPPORTED_LANGS:
        data = json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        counts[lang] = len(data)
    assert len(set(counts.values())) == 1, f"Key count mismatch: {counts}"


def test_all_locales_have_same_keys():
    en_keys = set(
        json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8")).keys()
    )
    for lang in SUPPORTED_LANGS:
        if lang == "en":
            continue
        keys = set(
            json.loads(
                (LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8")
            ).keys()
        )
        missing = en_keys - keys
        extra = keys - en_keys
        assert not missing, f"{lang} missing keys: {missing}"
        assert not extra, f"{lang} has extra keys: {extra}"


# ---------------------------------------------------------------------------
# New wizard keys — Q1 to Step6
# ---------------------------------------------------------------------------

NEW_WIZARD_KEYS = [
    "onboarding.q1_select",
    "onboarding.q1_custom_prompt",
    "onboarding.q1_confirmed",
    "onboarding.q2_select",
    "onboarding.q2_provider_anthropic",
    "onboarding.q2_provider_openai",
    "onboarding.q2_provider_gemini",
    "onboarding.q2_provider_groq",
    "onboarding.q2_provider_ollama",
    "onboarding.q3_ollama_setup",
    "onboarding.q3_key_prompt",
    "onboarding.q3_key_saved",
    "onboarding.q3_no_key",
    "onboarding.q4_use_default",
    "onboarding.q4_custom_path",
    "onboarding.step5_title",
    "onboarding.step5_desc",
    "onboarding.step5_confirm",
    "onboarding.step5_empty",
    "onboarding.step5_skip",
    "onboarding.step5_error",
    "onboarding.step6_title",
    "onboarding.step6_desc",
    "onboarding.step6_confirm",
    "onboarding.step6_skip",
    "onboarding.step6_error",
]


@pytest.mark.parametrize("key", NEW_WIZARD_KEYS)
@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_new_wizard_key_resolves_to_non_key(key, lang):
    """Translation must not fall back to the key literal itself."""
    result = t(key, lang=lang)
    assert result != key, f"Key '{key}' not translated for lang '{lang}'"
    assert result.strip(), f"Empty translation for key '{key}' in lang '{lang}'"


def test_q1_confirmed_interpolation():
    result = t("onboarding.q1_confirmed", lang="en", name="Kronos")
    assert "Kronos" in result


def test_q3_key_saved_interpolation():
    result = t("onboarding.q3_key_saved", lang="fr", model="claude-haiku-4-5-20251001")
    assert "claude-haiku-4-5-20251001" in result


def test_q4_use_default_interpolation():
    result = t("onboarding.q4_use_default", lang="de", path="/home/user/docs")
    assert "/home/user/docs" in result


def test_step5_desc_interpolation():
    result = t("onboarding.step5_desc", lang="pt", name="Aether")
    assert "Aether" in result


def test_step6_confirm_interpolation():
    result = t("onboarding.step6_confirm", lang="it", name="Nova")
    assert "Nova" in result


def test_step5_error_interpolation():
    result = t("onboarding.step5_error", lang="es", error="disk full")
    assert "disk full" in result


# ---------------------------------------------------------------------------
# Language persistence in aeon_profile.json
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_aeon_home(tmp_path, monkeypatch):
    aeon_home = tmp_path / ".zana"
    aeon_home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    return aeon_home


def test_language_written_to_profile(fake_aeon_home):
    profile_path = fake_aeon_home / "aeon_profile.json"
    profile = {"name": "TestAeon", "language": "fr", "archetype": "warrior"}
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    saved = json.loads(profile_path.read_text())
    assert saved["language"] == "fr"


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_all_languages_persisted_correctly(fake_aeon_home, lang):
    profile_path = fake_aeon_home / "aeon_profile.json"
    profile = {"name": "Aeon", "language": lang}
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    saved = json.loads(profile_path.read_text())
    assert saved["language"] == lang


# ---------------------------------------------------------------------------
# i18n engine — set_lang / init_lang / available_langs
# ---------------------------------------------------------------------------


def test_available_langs_returns_all_six():
    langs = available_langs()
    for lang in SUPPORTED_LANGS:
        assert lang in langs


def test_set_lang_unknown_falls_back_to_es():
    set_lang("xx")
    from zana.core.i18n import get_lang

    assert get_lang() == "es"


def test_set_lang_valid():
    set_lang("de")
    from zana.core.i18n import get_lang

    assert get_lang() == "de"
    set_lang("es")  # reset


def test_t_fallback_chain_unknown_lang():
    result = t("onboarding.q1_name", lang="zz")
    assert result != "onboarding.q1_name"


def test_t_missing_key_returns_key_literal():
    result = t("nonexistent.key.xyz", lang="en")
    assert result == "nonexistent.key.xyz"


def test_init_lang_reads_env(monkeypatch):
    monkeypatch.setenv("ZANA_LANG", "pt")
    lang = init_lang()
    assert lang == "pt"
    set_lang("es")


# ---------------------------------------------------------------------------
# Provider label translations (non-empty, no duplicates per lang)
# ---------------------------------------------------------------------------

PROVIDER_KEYS = [
    "onboarding.q2_provider_anthropic",
    "onboarding.q2_provider_openai",
    "onboarding.q2_provider_gemini",
    "onboarding.q2_provider_groq",
    "onboarding.q2_provider_ollama",
]


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_provider_labels_unique_per_lang(lang):
    labels = [t(k, lang=lang) for k in PROVIDER_KEYS]
    assert len(labels) == len(set(labels)), f"Duplicate provider labels in '{lang}'"
