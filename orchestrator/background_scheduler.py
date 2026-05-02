"""
ZANA Background Scheduler — asyncio-native, zero extra dependencies.

Runs recurring jobs inside the FastAPI process using asyncio tasks:
  - mine_trajectories()  every ZANA_MINE_INTERVAL_HOURS  (default 24h)
  - review_cycle()       every ZANA_CURATE_INTERVAL_HOURS (default 24h)

Wire into gateway lifespan:
    from orchestrator.background_scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app):
        await start_scheduler()
        yield
        await stop_scheduler()
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Coroutine, Any

logger = logging.getLogger("zana.scheduler")

_MINE_INTERVAL_H   = float(os.getenv("ZANA_MINE_INTERVAL_HOURS",   "24"))
_CURATE_INTERVAL_H = float(os.getenv("ZANA_CURATE_INTERVAL_HOURS", "24"))
_INITIAL_DELAY_S   = float(os.getenv("ZANA_SCHEDULER_INITIAL_DELAY", "300"))  # 5 min warm-up

_tasks: list[asyncio.Task] = []


# ── Job runners ───────────────────────────────────────────────────────────────

async def _run_mine() -> None:
    """Auto-mine trajectories and propose new WisdomRules."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from orchestrator.curator import SkillCurator
        from orchestrator.transport import transport_from_env
        from procedural_memory.manager import SkillRegistry

        registry = SkillRegistry()
        curator = SkillCurator(registry=registry, chronicler=None, transport=transport_from_env())
        result = await curator.mine_trajectories()
        logger.info(
            "[Scheduler] mine_trajectories done — mined=%s proposed=%s",
            result.get("mined", "?"), result.get("proposed", "?"),
        )
        _emit_sentinel("CivicLedgerEntry", {
            "job": "mine_trajectories",
            "result": result,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning("[Scheduler] mine_trajectories failed: %s", e)


async def _run_curate() -> None:
    """Review and prune stale skills via SkillCurator.review_cycle()."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from orchestrator.curator import SkillCurator
        from orchestrator.transport import transport_from_env
        from procedural_memory.manager import SkillRegistry

        registry = SkillRegistry()
        curator = SkillCurator(registry=registry, chronicler=None, transport=transport_from_env())
        result = await curator.review_cycle()
        logger.info(
            "[Scheduler] review_cycle done — reviewed=%s retired=%s improved=%s",
            result.get("reviewed", "?"), result.get("retired", "?"), result.get("improved", "?"),
        )
        _emit_sentinel("CivicLedgerEntry", {
            "job": "review_cycle",
            "result": result,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning("[Scheduler] review_cycle failed: %s", e)


# ── Periodic loop ─────────────────────────────────────────────────────────────

async def _periodic(name: str, coro_fn, interval_h: float, initial_delay_s: float) -> None:
    """Run coro_fn once every interval_h hours, starting after initial_delay_s seconds."""
    interval_s = interval_h * 3600
    logger.info(
        "[Scheduler] %s registered — interval=%.1fh initial_delay=%.0fs",
        name, interval_h, initial_delay_s,
    )
    await asyncio.sleep(initial_delay_s)
    while True:
        logger.info("[Scheduler] Running %s …", name)
        await coro_fn()
        logger.info("[Scheduler] %s complete — next run in %.1fh", name, interval_h)
        await asyncio.sleep(interval_s)


# ── Public API ────────────────────────────────────────────────────────────────

async def start_scheduler() -> None:
    """Start all background jobs. Call from FastAPI lifespan startup."""
    if _tasks:
        logger.warning("[Scheduler] Already started — skipping duplicate start")
        return

    jobs: list[tuple[str, Any, float]] = [
        ("mine_trajectories", _run_mine,   _MINE_INTERVAL_H),
        ("review_cycle",      _run_curate, _CURATE_INTERVAL_H),
    ]

    # Stagger initial delays to avoid both jobs hitting LLM simultaneously
    for i, (name, fn, interval_h) in enumerate(jobs):
        delay = _INITIAL_DELAY_S + i * 60  # 5m, 6m, ...
        task = asyncio.create_task(
            _periodic(name, fn, interval_h, delay),
            name=f"zana-scheduler-{name}",
        )
        _tasks.append(task)

    logger.info(
        "[Scheduler] Started %d background jobs (mine=%.1fh, curate=%.1fh, warm_up=%.0fs)",
        len(_tasks), _MINE_INTERVAL_H, _CURATE_INTERVAL_H, _INITIAL_DELAY_S,
    )


async def stop_scheduler() -> None:
    """Cancel all background jobs. Call from FastAPI lifespan shutdown."""
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    logger.info("[Scheduler] All background jobs stopped")


def scheduler_status() -> dict:
    """Returns current scheduler state for /health endpoint."""
    return {
        "running": len(_tasks),
        "jobs": [t.get_name() for t in _tasks if not t.done()],
        "mine_interval_h": _MINE_INTERVAL_H,
        "curate_interval_h": _CURATE_INTERVAL_H,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _emit_sentinel(event_type: str, payload: dict) -> None:
    """Fire a Sentinel event (best-effort)."""
    try:
        from sentinel.event_bus import get_bus, ZanaEvent, EventType
        asyncio.create_task(
            get_bus().emit(
                ZanaEvent(type=EventType(event_type), payload=payload, session_id="scheduler"),
                fire_and_forget=True,
            )
        )
    except Exception:
        pass
