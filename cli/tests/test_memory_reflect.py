"""Tests for EML — zana memory reflect, episodic fact extraction (S19-B)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_reflect(text: str) -> MagicMock:
    """Run cmd_memory_reflect with cmd_memory_add patched; return the mock."""
    with (
        patch("zana.commands.memory.cmd_memory_add") as mock_add,
        patch("zana.commands.memory.console"),
    ):
        from zana.commands.memory import cmd_memory_reflect

        cmd_memory_reflect(text)
    return mock_add


# ---------------------------------------------------------------------------
# Fact extraction tests
# ---------------------------------------------------------------------------


def test_reflect_extracts_name_english():
    mock_add = _run_reflect("my name is Ana García")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User identity: Ana García" in c for c in calls)


def test_reflect_extracts_name_spanish():
    mock_add = _run_reflect("me llamo Carlos")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User identity: Carlos" in c for c in calls)


def test_reflect_extracts_employer():
    mock_add = _run_reflect("I work at Vecanova")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User employer: Vecanova" in c for c in calls)


def test_reflect_extracts_employer_spanish():
    mock_add = _run_reflect("trabajo en Vecanova")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User employer: Vecanova" in c for c in calls)


def test_reflect_extracts_role():
    mock_add = _run_reflect("I am a software engineer")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User role: software engineer" in c for c in calls)


def test_reflect_extracts_location():
    mock_add = _run_reflect("I live in Medellín")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User location: Medellín" in c for c in calls)


def test_reflect_extracts_preference():
    mock_add = _run_reflect("I prefer Python over JavaScript")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User preference: Python over JavaScript" in c for c in calls)


def test_reflect_no_facts_message():
    """Short / pronoun-led text that matches no patterns — no add call."""
    with (
        patch("zana.commands.memory.cmd_memory_add") as mock_add,
        patch("zana.commands.memory.console") as mock_console,
    ):
        from zana.commands.memory import cmd_memory_reflect

        cmd_memory_reflect("the sky looks nice today")
    mock_add.assert_not_called()
    # Verify the "No facts detected" message was printed
    printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "No facts detected" in printed


def test_reflect_empty_text_warning():
    with (
        patch("zana.commands.memory.cmd_memory_add") as mock_add,
        patch("zana.commands.memory.console") as mock_console,
    ):
        from zana.commands.memory import cmd_memory_reflect

        cmd_memory_reflect("   ")
    mock_add.assert_not_called()
    printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "No text provided" in printed


def test_reflect_deduplicates_facts():
    mock_add = _run_reflect("my name is Ana. my name is Ana.")
    # The same fact should only be added once despite appearing twice
    identity_calls = [
        c for c in mock_add.call_args_list if "User identity: Ana" in c.args[0]
    ]
    assert len(identity_calls) == 1


def test_reflect_multiple_facts_in_one_text():
    mock_add = _run_reflect("my name is Ana. I work at Vecanova.")
    calls = [c.args[0] for c in mock_add.call_args_list]
    assert any("User identity: Ana" in c for c in calls)
    assert any("User employer: Vecanova" in c for c in calls)
    assert mock_add.call_count >= 2


def test_reflect_source_is_reflect():
    mock_add = _run_reflect("my name is Ana")
    for c in mock_add.call_args_list:
        assert c.kwargs.get("source") == "reflect"


def test_reflect_tag_is_episodic():
    mock_add = _run_reflect("my name is Ana")
    for c in mock_add.call_args_list:
        assert c.kwargs.get("tag") == "episodic"


# ---------------------------------------------------------------------------
# ZSM intent detection
# ---------------------------------------------------------------------------


def test_zsm_detects_reflect_intent():
    from zana.core.zsm import _detect_intent

    assert _detect_intent("reflect my name is Ana") == "memory_reflect"


def test_zsm_detects_extrae_hechos():
    from zana.core.zsm import _detect_intent

    assert _detect_intent("extrae hechos de este texto") == "memory_reflect"


def test_zsm_detects_refleja():
    from zana.core.zsm import _detect_intent

    assert _detect_intent("refleja este párrafo") == "memory_reflect"


def test_zsm_detects_analiza_esto():
    from zana.core.zsm import _detect_intent

    assert _detect_intent("analiza esto: me llamo Juan") == "memory_reflect"
