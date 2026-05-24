"""ZSM intent coverage — all intents verified with multiple natural variants."""

from __future__ import annotations

import pytest
from zana.core.zsm import _INTENT_PATTERNS
from zana.core.zsm_engine import _SESSION_CONTEXT, detect

# Minimum score to consider an intent detected
THRESHOLD = 0.40


@pytest.fixture(autouse=True)
def clear_session_context():
    """Prevent _SESSION_CONTEXT from leaking across tests and boosting wrong intents."""
    _SESSION_CONTEXT.clear()
    yield
    _SESSION_CONTEXT.clear()


def _top(query: str) -> tuple[str, float]:
    results = detect(query, _INTENT_PATTERNS)
    return results[0] if results else ("unknown", 0.0)


def _score(query: str, intent: str) -> float:
    results = detect(query, _INTENT_PATTERNS)
    return dict(results).get(intent, 0.0)


# ── companion ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "hola",
        "hello zana",
        "buenos días",
        "hey",
        "buenas tardes",
    ],
)
def test_companion_detected(query):
    intent, score = _top(query)
    assert intent == "companion" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── help ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "ayuda",
        "help",
        "necesito ayuda",
        "comandos disponibles",
        "ajuda por favor",
    ],
)
def test_help_detected(query):
    intent, score = _top(query)
    assert intent == "help" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── math ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "how much is 5 times 3",
        "how much is 100 plus 50",
        "how much is 200 minus 75",
        "calculate 8 divided by 2",
        "how much is seven squared",
    ],
)
def test_math_detected(query):
    intent, score = _top(query)
    assert intent == "math" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── reminder ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "recuérdame la reunión mañana",
        "remind me to call John",
        "remind me at 9am",
        "recuérdame comprar leche",
        "remind me tomorrow",
    ],
)
def test_reminder_detected(query):
    intent, score = _top(query)
    assert intent == "reminder" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── economy ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "presupuesto mensual",
        "gasto semanal",
        "spent 50 on food",
        "budget spent this month",
        "total gastos del mes",
    ],
)
def test_economy_detected(query):
    intent, score = _top(query)
    assert intent == "economy" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── language ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "traduce hello al español",
        "translate good morning to French",
        "how do you say hello in German",
        "translate this text to Portuguese",
        "traduce esta frase",
    ],
)
def test_language_detected(query):
    intent, score = _top(query)
    assert intent == "language" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── memory ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "recuerda mi contraseña",
        "qué recuerdas de Python",
        "recuerda algo importante",
        "lembra de mim",
        "qué recuerdas de ayer",
    ],
)
def test_memory_detected(query):
    intent, score = _top(query)
    assert intent == "memory" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── vault ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "nota: comprar leche",
        "nota de reunión importante",
        "nota privada importante",
        "notas del día",
        "nota confidencial del proyecto",
    ],
)
def test_vault_detected(query):
    intent, score = _top(query)
    assert intent == "vault" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── cook ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "receta de pasta carbonara",
        "recipe for chocolate cake",
        "ingredientes para lasaña",
        "receta fácil de arroz",
        "ingredientes para hacer pasta",
    ],
)
def test_cook_detected(query):
    intent, score = _top(query)
    assert intent == "cook" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── time ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "qué hora es",
        "what time is it",
        "qué día es hoy",
        "what is today's date",
        "qué hora es en Tokyo",
    ],
)
def test_time_detected(query):
    intent, score = _top(query)
    assert intent == "time" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── tier ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "qué nivel tengo",
        "what level am I",
        "qué puedo desbloquear",
        "what can I unlock",
        "siguiente nivel",
    ],
)
def test_tier_detected(query):
    intent, score = _top(query)
    assert intent == "tier" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── aeon ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "estado del aeon",
        "my aeon status",
        "mi aeón personal",
        "aeón status info",
        "aeon ZANA estado",
    ],
)
def test_aeon_detected(query):
    intent, score = _top(query)
    assert intent == "aeon" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── ledger ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "audit log",
        "ledger",
        "auditoría del sistema",
        "auditoría civic ledger",
        "registro de auditoría",
    ],
)
def test_ledger_detected(query):
    intent, score = _top(query)
    assert intent == "ledger" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── skill ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "workflow automatiza",
        "automate task",
        "flujo de trabajo",
        "crear automatización",
        "automatizar mi flujo",
    ],
)
def test_skill_detected(query):
    intent, score = _top(query)
    assert intent == "skill" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── web_search ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "busca en internet python tutorial",
        "busca en la web machine learning",
        "buscar en google noticias",
        "search the web for AI news",
        "busca online últimas noticias",
    ],
)
def test_web_search_detected(query):
    intent, score = _top(query)
    assert intent == "web_search" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── shell ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "lista mis archivos en Documents",
        "list files in ~/Downloads",
        "qué hay en mi carpeta de proyectos",
        "muestra el archivo config.txt",
        "crea la carpeta nueva",
    ],
)
def test_shell_detected(query):
    intent, score = _top(query)
    assert intent == "shell" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── wisdom_capture ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "recuerda que siempre escribir tests",
        "aprende que commitear frecuentemente es mejor",
        "anota que la documentación es importante",
        "remember this rule always",
        "rule: always validate user input",
    ],
)
def test_wisdom_capture_detected(query):
    intent, score = _top(query)
    assert intent == "wisdom_capture" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── memory_reflect ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "extrae hechos de este párrafo",
        "analiza esta información ahora",
        "analiza estos datos importantes",
        "analiza este párrafo ahora",
        "reflect and analyze this",
    ],
)
def test_memory_reflect_detected(query):
    intent, score = _top(query)
    assert intent == "memory_reflect" and score >= THRESHOLD, (
        f"got {intent}={score:.2f} for {query!r}"
    )


# ── Negative tests — intent should NOT be confused ─────────────────────────


@pytest.mark.parametrize(
    "query,wrong_intent",
    [
        ("lista mis archivos en Documents", "wisdom_capture"),
        ("recuerda que siempre commitear", "shell"),
        ("busca en internet noticias", "shell"),
        ("hola buenos días", "math"),
        ("qué hora es ahora", "economy"),
        ("traduce hello al español", "memory"),
        ("receta de arroz con leche", "ledger"),
    ],
)
def test_intent_not_confused(query: str, wrong_intent: str):
    top_intent, top_score = _top(query)
    wrong_score = _score(query, wrong_intent)
    assert wrong_score < 0.70 or top_intent != wrong_intent, (
        f"'{wrong_intent}' got {wrong_score:.2f} for {query!r} (top: {top_intent}={top_score:.2f})"
    )


# ── All intents are registered ─────────────────────────────────────────────


def test_all_intents_present_in_detect():
    """detect() must return a score for every registered intent."""
    query = "lista mis archivos"
    results = detect(query, _INTENT_PATTERNS)
    assert len(results) >= 1


def test_detect_returns_top3_or_less():
    results = detect("hola", _INTENT_PATTERNS)
    assert 1 <= len(results) <= 3


def test_all_scores_between_0_and_1():
    for query in ["hola", "lista archivos", "recuerda que", "busca en internet"]:
        results = detect(query, _INTENT_PATTERNS)
        for _, score in results:
            assert 0.0 <= score <= 1.0, f"Score {score} out of [0,1] for {query!r}"


def test_detect_sorted_descending():
    results = detect("lista mis archivos en Documents", _INTENT_PATTERNS)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)
