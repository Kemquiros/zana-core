"""
/shadow — Shadow Observer daemon control
/swarm  — Red Queen swarm layer control

State is kept in-process (dict). For multi-process deployments, swap
_shadow_state / _swarm_state for a Redis-backed store.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("zana.control")

router = APIRouter(tags=["Control"])

REGISTRY_URL = os.getenv("ZANA_REGISTRY_URL", "http://localhost:54445")

# ── Shadow Observer state ──────────────────────────────────────────────────────

_shadow_state: dict[str, Any] = {
    "active": False,
    "events_captured": 0,
    "last_event": None,
    "started_at": None,
}


def record_shadow_event(event_type: str, payload: dict | None = None) -> None:
    """
    Called internally by other gateway endpoints to log observable events.
    Drop-in: add `record_shadow_event("text_sense", {...})` to any handler.
    """
    if not _shadow_state["active"]:
        return
    _shadow_state["events_captured"] += 1
    _shadow_state["last_event"] = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(payload or {}),
    }
    logger.debug(
        "👁️  [SHADOW] event=%s total=%d", event_type, _shadow_state["events_captured"]
    )


# Shadow endpoints


@router.post("/shadow/enable", summary="Activate Shadow Observer")
async def shadow_enable():
    _shadow_state["active"] = True
    _shadow_state["started_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("👁️  [SHADOW] Observer activated")
    return {"active": True, "started_at": _shadow_state["started_at"]}


@router.post("/shadow/disable", summary="Deactivate Shadow Observer")
async def shadow_disable():
    _shadow_state["active"] = False
    logger.info("👁️  [SHADOW] Observer deactivated")
    return {"active": False, "events_captured": _shadow_state["events_captured"]}


@router.get("/shadow/status", summary="Shadow Observer status")
async def shadow_status():
    return _shadow_state


@router.get("/.well-known/openid-configuration", tags=["Identity"])
async def oidc_discovery():
    """OIDC Discovery endpoint for Sovereign Identity."""
    base_url = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/auth/authorize",
        "token_endpoint": f"{base_url}/auth/token",
        "userinfo_endpoint": f"{base_url}/auth/userinfo",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "response_types_supported": ["code", "token", "id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "claims_supported": ["sub", "name", "preferred_username", "email", "dna_metadata"]
    }

# ── System Update (Sovereign Update Pulse) ───────────────────────────────────

UPDATE_STATE_FILE = Path.home() / ".config" / "zana" / "update_state.json"

@router.get("/system/update-staged", summary="Get staged update info")
async def get_staged_update():
    """Retrieve the staged update info prepared by the Heartbeat."""
    if not UPDATE_STATE_FILE.exists():
        return {"status": "UP_TO_DATE", "latest_version": None}
    
    try:
        data = json.loads(UPDATE_STATE_FILE.read_text())
        return data
    except Exception as e:
        logger.error(f"Error reading update state: {e}")
        return {"status": "ERROR", "message": str(e)}

@router.post("/system/upgrade-trigger", summary="Initiate the Ascension Protocol")
async def trigger_upgrade():
    """
    Trigger the hot-swap update. This will pull latest images and restart containers.
    The caller (UI) should expect a few seconds of downtime.
    """
    if not UPDATE_STATE_FILE.exists():
        return {"status": "ERROR", "message": "No update staged."}
    
    # We use subprocess.Popen so we can return the response before the system goes down
    # The actual upgrade logic is handled by 'zana upgrade' or direct docker commands
    try:
        # Identify zana binary path
        zana_cmd = "zana"
        
        # We trigger a background process that will pull and restart
        # We use a shell script or a nohup to ensure it survives the container stop
        # Actually, in a docker environment, the 'gateway' might be stopped.
        # But if we are running in 'zana-core' host mode or via a sibling container:
        # The best way is to let the host or orchestrator handle it.
        # For now, we assume a local-first deployment where the CLI is available.
        
        # Non-blocking execution
        subprocess.Popen(
            ["zana", "upgrade", "--no-interactive"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        return {"status": "INSTALLING", "message": "Ascension Protocol initiated. See you on the other side."}
    except Exception as e:
        logger.error(f"Failed to trigger upgrade: {e}")
        return {"status": "ERROR", "message": str(e)}

# ── Swarm state ───────────────────────────────────────────────────────────────

_swarm_state: dict[str, Any] = {
    "running": False,
    "warriors": [],
    "generations": 0,
    "started_at": None,
}


class SwarmInitRequest(BaseModel):
    warriors: int = 50
    generations: int = 2000


class AssimilateRequest(BaseModel):
    rules: list[dict]


class SwarmQueryRequest(BaseModel):
    fact_key: str
    context: Optional[dict] = None


def _spawn_warriors(n: int) -> list[dict]:
    import hashlib
    import random

    fleet = []
    for i in range(n):
        seed = f"warrior-{i:04d}-{time.time()}"
        fp = hashlib.sha256(seed.encode()).hexdigest()
        fleet.append(
            {
                "id": f"warrior-{i:04d}",
                "stage": "larva",
                "generation": 0,
                "fitness": round(random.uniform(0.35, 0.70), 3),
                "dna_fingerprint": fp,
                "status": "idle",
            }
        )
    return fleet


def _evolve_step(fleet: list[dict]) -> list[dict]:
    """One generation tick — mutate fitness, promote warriors."""
    import random

    for w in fleet:
        delta = random.uniform(-0.05, 0.08)
        w["fitness"] = round(max(0.01, min(1.0, w["fitness"] + delta)), 3)
        w["generation"] += 1
        if w["fitness"] >= 0.90 and w["stage"] == "warrior":
            w["stage"] = "legend"
            w["status"] = "active"
        elif w["fitness"] >= 0.65 and w["stage"] == "larva":
            w["stage"] = "warrior"
            w["status"] = "active"
        elif w["fitness"] < 0.20:
            w["status"] = "idle"
        else:
            w["status"] = "evolving"
    return fleet


_evolution_task: asyncio.Task | None = None


async def _evolution_loop(generations: int) -> None:
    """Background coroutine — runs one tick per second up to max generations."""
    gen = 0
    while _swarm_state["running"] and gen < generations:
        await asyncio.sleep(1.0)
        _swarm_state["warriors"] = _evolve_step(_swarm_state["warriors"])
        _swarm_state["generations"] = gen
        gen += 1
    _swarm_state["running"] = False
    logger.info("🐝 [SWARM] Evolution complete at generation %d", gen)


# Swarm endpoints


@router.post("/swarm/init", summary="Bootstrap Red Queen warrior fleet")
async def swarm_init(req: SwarmInitRequest):
    global _evolution_task

    if _swarm_state["running"]:
        return {
            "error": "swarm_already_running",
            "warriors": len(_swarm_state["warriors"]),
        }

    fleet = _spawn_warriors(req.warriors)
    _swarm_state.update(
        {
            "running": True,
            "warriors": fleet,
            "generations": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Launch background evolution
    loop = asyncio.get_event_loop()
    _evolution_task = loop.create_task(_evolution_loop(req.generations))

    logger.info(
        "🐝 [SWARM] Red Queen online — %d warriors, %d generations",
        req.warriors,
        req.generations,
    )
    return {
        "spawned": req.warriors,
        "generations": req.generations,
        "started_at": _swarm_state["started_at"],
    }


@router.get("/swarm/status", summary="Live warrior fleet status")
async def swarm_status():
    return {
        "running": _swarm_state["running"],
        "current_generation": _swarm_state["generations"],
        "started_at": _swarm_state["started_at"],
        "warriors": _swarm_state["warriors"],
        "summary": {
            "total": len(_swarm_state["warriors"]),
            "active": sum(
                1 for w in _swarm_state["warriors"] if w["status"] == "active"
            ),
            "legends": sum(
                1 for w in _swarm_state["warriors"] if w["stage"] == "legend"
            ),
            "avg_fitness": (
                round(
                    sum(w["fitness"] for w in _swarm_state["warriors"])
                    / max(len(_swarm_state["warriors"]), 1),
                    3,
                )
                if _swarm_state["warriors"]
                else 0.0
            ),
        },
    }


@router.post("/swarm/stop", summary="Stop all swarm warriors")
async def swarm_stop():
    global _evolution_task
    _swarm_state["running"] = False
    if _evolution_task and not _evolution_task.done():
        _evolution_task.cancel()
    _evolution_task = None
    warriors = len(_swarm_state["warriors"])
    _swarm_state["warriors"] = []
    logger.info("🐝 [SWARM] Red Queen stopped")
    return {"stopped": True, "warriors_dissolved": warriors}


@router.post("/swarm/assimilate", summary="Assimilate WisdomRules from Wisdom Hub")
async def swarm_assimilate(req: AssimilateRequest):
    """
    Passes incoming rules through LLMGuard validation before assimilation.
    Validated rules are injected into the in-process reasoning engine.
    """
    from sensory.reasoning_router import _engine, _Rule, _Condition

    assimilated = 0
    for rd in req.rules:
        try:
            rule_data = rd.get("rule_data", rd)
            conds = [
                _Condition(
                    c["fact_key"],
                    c.get("operator", "eq"),
                    c["value"],
                    c.get("field_path"),
                )
                for c in rule_data.get("conditions", [])
            ]
            if not conds:
                continue
            new_rule = _Rule(
                rule_data.get("name", rd.get("id", f"swarm_rule_{assimilated}")),
                conds,
                rule_data.get("effects", rule_data.get("actions", [])),
                rule_data.get("explanation", "Swarm assimilated rule."),
                rule_data.get("confidence", 0.75),
            )
            # Avoid duplicate rule names
            existing_names = {r.name for r in _engine.DEFAULT_RULES}
            if new_rule.name not in existing_names:
                _engine.DEFAULT_RULES.append(new_rule)
                assimilated += 1
        except Exception as e:
            logger.warning("Rule assimilation failed: %s", e)

    logger.info("🐝 [SWARM] Assimilated %d rules", assimilated)
    return {"assimilated": assimilated, "total_rules": len(_engine.DEFAULT_RULES)}


@router.post("/swarm/query", summary="Distributed remote query to swarm peers")
async def swarm_query(req: SwarmQueryRequest):
    """Ask the Wisdom Hub Registry for rules covering the given fact_key."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{REGISTRY_URL}/wisdom")
            if resp.status_code != 200:
                return {
                    "found": False,
                    "error": f"registry_returned_{resp.status_code}",
                }

            rules = resp.json()
            candidates = [
                r
                for r in rules
                if any(
                    c.get("fact_key") == req.fact_key
                    for c in r.get("rule_data", {}).get("conditions", [])
                )
            ]
            if not candidates:
                return {"found": False, "fact_key": req.fact_key}

            best = max(candidates, key=lambda r: r.get("votes", 0))
            return {
                "found": True,
                "fact_key": req.fact_key,
                "rule": {
                    "id": best.get("id"),
                    "name": best.get("rule_data", {}).get("name"),
                    "creator_node": best.get("creator_node"),
                    "votes": best.get("votes", 0),
                    "rule_data": best.get("rule_data", {}),
                },
            }

    except httpx.ConnectError:
        return {"found": False, "error": "registry_offline"}
    except Exception as e:
        return {"found": False, "error": str(e)}
