"""
Sentinel Router — /sentinel endpoints for event bus observability (v3.0).

  GET  /sentinel/status          — bus health + event type counts
  GET  /sentinel/events          — recent event ring buffer
  GET  /sentinel/ledger          — last N entries from Civic Ledger (~/.zana/civic_ledger.jsonl)
  POST /sentinel/emit            — manually emit a test event (dev/debug only)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("zana.sentinel_router")
router = APIRouter(prefix="/sentinel", tags=["sentinel"])

_LEDGER_PATH = Path.home() / ".zana" / "civic_ledger.jsonl"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/status")
async def sentinel_status():
    """Sentinel Event Bus health and event statistics."""
    try:
        from sentinel.event_bus import get_bus, EventType
        bus = get_bus()
        counts = bus.stats()
        return {
            "status": "online",
            "event_types": [e.value for e in EventType],
            "stats": counts,
            "buffer_size": len(bus.recent_events(500)),
            "ledger_entries": _count_ledger(),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/events")
async def sentinel_events(
    limit: int = Query(default=50, ge=1, le=500),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
):
    """Recent events from the in-memory ring buffer."""
    try:
        from sentinel.event_bus import get_bus
        bus = get_bus()
        return {
            "events": bus.recent_events(limit=limit, event_type=event_type),
            "total_in_buffer": len(bus.recent_events(500)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger")
async def sentinel_ledger(
    limit: int = Query(default=100, ge=1, le=1000),
    event_type: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
):
    """Read recent entries from the Civic Ledger (~/.zana/civic_ledger.jsonl)."""
    if not _LEDGER_PATH.exists():
        return {"entries": [], "total": 0}

    entries: list[dict] = []
    try:
        lines = _LEDGER_PATH.read_text().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type and entry.get("event_type") != event_type:
                continue
            if session_id and entry.get("session_id") != session_id:
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"entries": entries, "total": _count_ledger()}


class EmitRequest(BaseModel):
    event_type: str
    payload: dict = {}
    session_id: str = "debug"


@router.post("/emit")
async def sentinel_emit(req: EmitRequest):
    """Manually emit an event for testing/debugging."""
    try:
        from sentinel.event_bus import get_bus, ZanaEvent, EventType
        event_type = EventType(req.event_type)
        bus = get_bus()
        await bus.emit(
            ZanaEvent(type=event_type, payload=req.payload, session_id=req.session_id),
            fire_and_forget=False,
        )
        return {"emitted": event_type, "session_id": req.session_id}
    except ValueError:
        from sentinel.event_bus import EventType
        valid = [e.value for e in EventType]
        raise HTTPException(status_code=400, detail=f"Unknown event type. Valid: {valid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _count_ledger() -> int:
    if not _LEDGER_PATH.exists():
        return 0
    try:
        return sum(1 for line in _LEDGER_PATH.read_text().splitlines() if line.strip())
    except Exception:
        return -1
