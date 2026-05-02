"""
Wisdom Router — /wisdom endpoints for Auto-WisdomRules inbox (v3.0).

GET  /wisdom/inbox          — list pending proposed skills
POST /wisdom/approve/{id}   — approve → register as active skill
POST /wisdom/reject/{id}    — reject and remove from inbox
POST /wisdom/mine           — trigger manual trajectory mining
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("WisdomRouter")
router = APIRouter(prefix="/wisdom", tags=["wisdom"])

_WISDOM_INBOX_PATH = Path(__file__).parent / "data" / "wisdom_inbox.json"


def _load_inbox() -> dict:
    if _WISDOM_INBOX_PATH.exists():
        try:
            return json.loads(_WISDOM_INBOX_PATH.read_text())
        except Exception:
            pass
    return {"pending": [], "approved": [], "rejected": []}


def _save_inbox(inbox: dict) -> None:
    _WISDOM_INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _WISDOM_INBOX_PATH.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))


class ApproveRequest(BaseModel):
    skill_id_override: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/inbox")
async def get_wisdom_inbox():
    """Return all pending wisdom proposals for user review."""
    inbox = _load_inbox()
    pending = inbox.get("pending", [])
    approved = inbox.get("approved", [])
    rejected = inbox.get("rejected", [])
    return {
        "pending": pending,
        "stats": {
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
        },
    }


@router.post("/approve/{wisdom_id}")
async def approve_wisdom(wisdom_id: str, body: ApproveRequest = ApproveRequest()):
    """Approve a pending wisdom rule → registers it as an active skill."""
    inbox = _load_inbox()
    pending = inbox.get("pending", [])

    proposal = next((p for p in pending if p["id"] == wisdom_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Wisdom ID '{wisdom_id}' not found in inbox")

    # Register as active skill via SkillRegistry
    try:
        from procedural_memory.manager import SkillRegistry
        reg = SkillRegistry()
        skill_id = body.skill_id_override or f"wisdom_{wisdom_id}"
        reg.register_skill(
            skill_id=skill_id,
            name=proposal["name"],
            steps=proposal.get("steps", []),
            domain=proposal.get("domain", "general"),
        )
        # Tag as auto-generated from wisdom mining
        if skill_id in reg.skills:
            reg.skills[skill_id]["source"] = "auto_wisdom_mining"
            reg.skills[skill_id]["trigger"] = proposal.get("trigger", "")
            reg.skills[skill_id]["confidence_at_proposal"] = proposal.get("confidence", 0.5)
            reg.save()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register skill: {e}")

    # Move from pending → approved
    proposal["approved_at"] = datetime.now().isoformat()
    proposal["status"] = "approved"
    proposal["registered_skill_id"] = skill_id
    inbox["pending"] = [p for p in pending if p["id"] != wisdom_id]
    inbox.setdefault("approved", []).append(proposal)
    _save_inbox(inbox)

    logger.info(f"WisdomRule '{proposal['name']}' approved → skill '{skill_id}'")
    return {"status": "approved", "skill_id": skill_id, "name": proposal["name"]}


@router.post("/reject/{wisdom_id}")
async def reject_wisdom(wisdom_id: str):
    """Reject a pending wisdom proposal."""
    inbox = _load_inbox()
    pending = inbox.get("pending", [])

    proposal = next((p for p in pending if p["id"] == wisdom_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Wisdom ID '{wisdom_id}' not found")

    proposal["rejected_at"] = datetime.now().isoformat()
    proposal["status"] = "rejected"
    inbox["pending"] = [p for p in pending if p["id"] != wisdom_id]
    inbox.setdefault("rejected", []).append(proposal)
    _save_inbox(inbox)

    return {"status": "rejected", "id": wisdom_id}


@router.post("/mine")
async def trigger_mining():
    """Manually trigger trajectory mining to generate new wisdom proposals."""
    try:
        from orchestrator.curator import SkillCurator, _load_wisdom_inbox
        from procedural_memory.manager import SkillRegistry

        reg = SkillRegistry()
        curator = SkillCurator(registry=reg, chronicler=None)
        result = await curator.mine_trajectories()
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Mining trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
