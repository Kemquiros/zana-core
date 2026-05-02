"""
Sentinel hooks for the CLI — PRE_TOOL_USE and POST_TOOL_USE lifecycle events.

Sync-safe: bridges the async event bus from synchronous Typer commands.
Usage (via main.py callback): auto-wired, no direct calls needed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("zana.cli.sentinel")

# Commands excluded from PRE/POST tracking (noise, not tools)
_EXCLUDED = frozenset({"--help", "--version", "help", "completion"})


def _sync_emit(event_type_value: str, payload: dict[str, Any]) -> None:
    """Fire a sentinel event from a synchronous context (best-effort, never raises)."""
    try:
        from sentinel.event_bus import get_bus, ZanaEvent, EventType
        event = ZanaEvent(
            type=EventType(event_type_value),
            payload=payload,
            session_id="cli",
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(get_bus().emit(event, fire_and_forget=True))
            else:
                loop.run_until_complete(get_bus().emit(event, fire_and_forget=False))
        except RuntimeError:
            asyncio.run(get_bus().emit(event, fire_and_forget=False))
    except Exception as _e:
        logger.debug("Sentinel CLI emit skipped: %s", _e)


def fire_pre_tool_use(command: str, params: dict[str, Any] | None = None) -> None:
    if command in _EXCLUDED:
        return
    _sync_emit("PreToolUse", {"tool": f"zana:{command}", "params": params or {}})


def fire_post_tool_use(command: str, success: bool = True, elapsed_ms: float = 0.0) -> None:
    if command in _EXCLUDED:
        return
    _sync_emit("PostToolUse", {
        "tool": f"zana:{command}",
        "success": success,
        "elapsed_ms": round(elapsed_ms, 2),
    })


@contextmanager
def sentinel_tool_scope(command: str, params: dict[str, Any] | None = None):
    """Context manager that fires PRE before and POST after a CLI tool block."""
    fire_pre_tool_use(command, params)
    t0 = time.perf_counter()
    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fire_post_tool_use(command, success=success, elapsed_ms=elapsed_ms)
