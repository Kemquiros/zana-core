"""
ZSM (ZANA Sovereign Machine) intent test suite — Sprint 8.

Covers all 15 intent categories declared in zsm.py._INTENT_PATTERNS.
Each test verifies that:
  1. _detect_intent() routes the query to the correct intent bucket.
  2. respond_text() returns a non-empty string without raising.

No network, no Docker, no LLM required — 100% offline.
"""

import pytest
from zana.core.zsm import ZSMEngine, _detect_intent


@pytest.fixture(scope="module")
def engine() -> ZSMEngine:
    return ZSMEngine(lang="en")


# ---------------------------------------------------------------------------
# Intent routing — _detect_intent()
#
# Queries are chosen to contain only keywords from the target intent bucket
# and NOT keywords from any earlier-ordered bucket (companion, help, math …).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected_intent",
    [
        # companion — "hello", "how are you", "hi "
        ("hello zana", "companion"),
        ("how are you doing today", "companion"),
        # help — "help", "commands", "what can you"
        ("what can you do for me", "help"),
        ("show commands list", "help"),
        # math — regex triggers on operator-between-digits
        ("12 * 8 equals?", "math"),
        ("100 / 4 please", "math"),
        # reminder — "remind me", "alert me"
        ("remind me to call Alice", "reminder"),
        ("alert me at noon", "reminder"),
        # economy — "spent", "expenses", "budget"
        ("I spent 50 on groceries", "economy"),
        ("show my expenses summary", "economy"),
        # language — "translate", "how do you say"
        ("traduce gracias to English", "language"),
        ("how do you say goodbye in French", "language"),
        # memory — "remember", "yesterday", "before"
        ("remember this project note", "memory"),
        ("what did we discuss yesterday", "memory"),
        # vault — "vault", "note", "file"
        ("search vault for API keys", "vault"),
        ("open file project_notes.md", "vault"),
        # cook — "receta", "recipe"
        ("receta de pasta carbonara", "cook"),
        ("what recipe uses eggs and cheese", "cook"),
        # time — "time", "date"
        ("what time is it now", "time"),
        ("current date please", "time"),
        # tier — "tier", "level", "aeon level"  (uses "tier" keyword)
        ("what tier am I on currently", "tier"),
        # aeon — "aeon"
        ("show aeon status info", "aeon"),
        ("aeon dna report", "aeon"),
        # ledger — "ledger"
        ("show civic ledger entries", "ledger"),
        ("ledger summary count", "ledger"),
        # skill — "skill"
        ("list my skill registry", "skill"),
        ("what skill can handle this task", "skill"),
    ],
)
def test_intent_routing(query: str, expected_intent: str) -> None:
    detected = _detect_intent(query)
    assert detected == expected_intent, (
        f"Query '{query}' → got '{detected}', expected '{expected_intent}'"
    )


# ---------------------------------------------------------------------------
# respond_text() — smoke test: no crash, non-empty output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "hello zana",
        "what can you do",
        "12 + 5",
        "what time is it",
        "show tier info",
        "traduce gracias to English",
        "remember this note",
        "show civic ledger",
        "aeon status",
        "list skill registry",
        "remind me to review PR",
        "I spent 15 on coffee",
    ],
)
def test_respond_text_does_not_crash(engine: ZSMEngine, query: str) -> None:
    result = engine.respond_text(query)
    assert isinstance(result, str)
    assert len(result) > 0, f"respond_text returned empty string for: '{query}'"


# ---------------------------------------------------------------------------
# Math intent — correctness (operator between digits → regex fires)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected_substring",
    [
        ("2 + 2", "4"),
        ("10 * 5", "50"),
        ("100 / 4", "25"),
    ],
)
def test_math_correct_result(
    engine: ZSMEngine, query: str, expected_substring: str
) -> None:
    result = engine.respond_text(query)
    assert expected_substring in result, (
        f"Math query '{query}' → '{result}' — expected '{expected_substring}'"
    )


# ---------------------------------------------------------------------------
# Time intent — returns recognisable time/date info
# ---------------------------------------------------------------------------


def test_time_returns_digits(engine: ZSMEngine) -> None:
    result = engine.respond_text("what time is it now")
    assert any(ch.isdigit() for ch in result), (
        f"Time response has no digits: '{result}'"
    )


# ---------------------------------------------------------------------------
# Unknown query falls back gracefully
# ---------------------------------------------------------------------------


def test_unknown_query_does_not_crash(engine: ZSMEngine) -> None:
    result = engine.respond_text("zxqwerty asdfghjkl unknown gibberish")
    assert isinstance(result, str)
    assert len(result) > 0
