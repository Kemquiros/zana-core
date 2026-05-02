"""
Sentinel Event Bus — core pub/sub infrastructure.

8 lifecycle events for policy control (Z-Sovereign protocol).
No ZANA module imports — this file is a pure infrastructure layer
that can be imported from anywhere without circular dependencies.

Usage:
    from sentinel.event_bus import get_bus, EventType, ZanaEvent

    # Subscribe (at module load time)
    bus = get_bus()
    bus.subscribe(EventType.PRE_TOOL_USE, my_handler)

    # Fire (anywhere in the codebase)
    await bus.emit(ZanaEvent(
        type=EventType.PRE_TOOL_USE,
        payload={"tool": "bash", "input": "ls /"},
        session_id="tg-12345",
    ))
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger("zana.sentinel")


# ── 8 Lifecycle Events ────────────────────────────────────────────────────────

class EventType(str, Enum):
    PRE_TOOL_USE      = "PreToolUse"
    POST_TOOL_USE     = "PostToolUse"
    SKILL_ACTIVATION  = "SkillActivation"
    ZSYNC_REQUEST     = "ZSyncRequest"
    EXTERNAL_API      = "ExternalAPI"
    MEMORY_WRITE      = "MemoryWrite"
    CIVIC_LEDGER_ENTRY = "CivicLedgerEntry"
    AEON_EVOLUTION    = "AeonEvolution"


# ── Event dataclass ───────────────────────────────────────────────────────────

@dataclass
class ZanaEvent:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    session_id: str = "global"
    aeon_id: str = "default"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def civic_hash(self) -> str:
        """Deterministic SHA-256 fingerprint of this event."""
        canonical = json.dumps(
            {
                "type": self.type,
                "payload": self.payload,
                "session_id": self.session_id,
                "aeon_id": self.aeon_id,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


HandlerFn = Callable[[ZanaEvent], Awaitable[None]]


# ── Event Bus ─────────────────────────────────────────────────────────────────

class EventBus:
    """
    Lightweight async pub/sub bus for ZANA lifecycle events.

    - Handlers are async callables.
    - Handler failures are logged but never propagate to callers.
    - emit() with fire_and_forget=True (default) returns immediately.
    - emit() with fire_and_forget=False awaits all handlers (for testing).
    - Recent events kept in a bounded ring buffer for /sentinel/events endpoint.
    """

    def __init__(self, buffer_size: int = 500):
        self._handlers: dict[EventType, list[HandlerFn]] = defaultdict(list)
        self._wildcard: list[HandlerFn] = []
        self._buffer: list[dict] = []
        self._buffer_size = buffer_size
        self._stats: dict[str, int] = defaultdict(int)

    def subscribe(self, event_type: EventType, handler: HandlerFn) -> None:
        """Register an async handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: HandlerFn) -> None:
        """Register an async handler that receives every event type."""
        self._wildcard.append(handler)

    def unsubscribe(self, event_type: EventType, handler: HandlerFn) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: ZanaEvent, fire_and_forget: bool = True) -> None:
        """Emit an event, invoking all registered handlers."""
        self._stats[event.type] += 1
        self._stats["total"] += 1

        # Buffer for introspection
        self._buffer.append({
            "type": event.type,
            "session_id": event.session_id,
            "aeon_id": event.aeon_id,
            "timestamp": event.timestamp,
            "civic_hash": event.civic_hash,
            "payload_keys": list(event.payload.keys()),
        })
        if len(self._buffer) > self._buffer_size:
            self._buffer.pop(0)

        handlers = self._handlers.get(event.type, []) + self._wildcard
        if not handlers:
            return

        if fire_and_forget:
            asyncio.create_task(self._dispatch(event, handlers))
        else:
            await self._dispatch(event, handlers)

    async def _dispatch(self, event: ZanaEvent, handlers: list[HandlerFn]) -> None:
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.warning(
                    "Sentinel handler %s failed for %s: %s",
                    getattr(handler, "__name__", repr(handler)),
                    event.type,
                    e,
                )

    def recent_events(self, limit: int = 50, event_type: str | None = None) -> list[dict]:
        events = self._buffer[-limit:]
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return list(reversed(events))

    def stats(self) -> dict:
        return dict(self._stats)


# ── Global singleton ──────────────────────────────────────────────────────────

_bus: EventBus | None = None


def get_bus() -> EventBus:
    """Return the global Sentinel event bus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
        _wire_default_handlers(_bus)
        logger.info("✓ Sentinel Event Bus initialized — 8 lifecycle events active")
    return _bus


# ── Default handlers ──────────────────────────────────────────────────────────

def _wire_default_handlers(bus: EventBus) -> None:
    """Wire built-in handlers: Civic Ledger audit + console debug log."""
    bus.subscribe_all(_civic_ledger_handler)


async def emit_aeon_evolution(old_rank: str, new_rank: str, aeon_id: str = "default", session_id: str = "global") -> None:
    """Convenience function to emit an AeonEvolution event when Mastery Map rank changes."""
    bus = get_bus()
    await bus.emit(
        ZanaEvent(
            type=EventType.AEON_EVOLUTION,
            payload={"old_rank": old_rank, "new_rank": new_rank},
            aeon_id=aeon_id,
            session_id=session_id,
        ),
        fire_and_forget=True,
    )


async def _civic_ledger_handler(event: ZanaEvent) -> None:
    """Write every event to the Civic Ledger (SHA-256 audit trail)."""
    from pathlib import Path
    import json as _json

    ledger_path = Path.home() / ".zana" / "civic_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "event_type": event.type,
        "session_id": event.session_id,
        "aeon_id": event.aeon_id,
        "timestamp": event.timestamp,
        "civic_hash": event.civic_hash,
        "payload": event.payload,
    }
    with ledger_path.open("a") as f:
        f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
