"""
wisdom_queue.py — Local JSON queue for Wisdom proposals (SPROUT tier).

Provides offline read/write/approve/reject for zana wisdom commands
when the Gateway is unreachable. Data lives at ~/.zana/wisdom_queue.json.
"""

from __future__ import annotations

import difflib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

QUEUE_PATH = Path.home() / ".zana" / "wisdom_queue.json"

_EMPTY: dict = {"pending": [], "approved": [], "rejected": []}


class WisdomQueue:
    """Manages ~/.zana/wisdom_queue.json as a local offline wisdom store.

    Schema:
    {
      "pending":  [{"id": str, "name": str, "domain": str, "confidence": float,
                    "trigger": str, "steps": list, "created_at": str}],
      "approved": [same shape + "approved_at": str],
      "rejected": [same shape + "rejected_at": str]
    }
    """

    def load(self) -> dict:
        """Return the queue dict, creating the file if it does not exist."""
        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not QUEUE_PATH.exists():
            self.save(dict(_EMPTY))
            return {"pending": [], "approved": [], "rejected": []}
        try:
            data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
            data.setdefault("pending", [])
            data.setdefault("approved", [])
            data.setdefault("rejected", [])
            return data
        except (json.JSONDecodeError, OSError):
            return {"pending": [], "approved": [], "rejected": []}

    def save(self, data: dict) -> None:
        """Write queue to disk atomically (write to .tmp then rename)."""
        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = QUEUE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, QUEUE_PATH)

    def inbox(self) -> list[dict]:
        """Return the list of pending proposals."""
        return self.load()["pending"]

    def stats(self) -> dict:
        """Return absorption analytics for the WisdomQueue.

        Legacy keys (``pending``, ``approved``, ``rejected``) are included
        alongside the new verbose keys for backward compatibility.
        """
        data = self.load()
        pending = data.get("pending", [])
        approved = data.get("approved", [])
        rejected = data.get("rejected", [])
        total = len(pending) + len(approved) + len(rejected)
        auto_approved = [r for r in approved if r.get("auto_approved")]
        return {
            # Verbose keys (S21-D)
            "pending_count": len(pending),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "total_proposed": total,
            "auto_approved_count": len(auto_approved),
            "absorption_rate": len(approved) / max(1, total),
            "avg_confidence": sum(r.get("confidence", 0) for r in approved)
            / max(1, len(approved)),
            # Legacy aliases (backward compat)
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
        }

    def _dedup_check(self, rule: dict) -> bool:
        """Return True if *rule* is a near-duplicate of any pending or approved rule.

        Uses difflib.SequenceMatcher; ratio > 0.85 counts as duplicate.
        """
        data = self.load()
        candidate_text = rule.get("text", rule.get("trigger", ""))
        for bucket in ("pending", "approved"):
            for existing in data.get(bucket, []):
                existing_text = existing.get("text", existing.get("trigger", ""))
                ratio = difflib.SequenceMatcher(
                    None, candidate_text, existing_text
                ).ratio()
                if ratio > 0.85:
                    return True
        return False

    def add(self, rule: dict) -> str:
        """Add *rule* to the queue with dedup + auto-approve logic.

        Returns:
            "duplicate"     — near-duplicate detected, rule not added.
            "auto_approved" — confidence >= 0.90, moved directly to approved.
            "pending"       — added to pending list (normal flow).
        """
        if self._dedup_check(rule):
            return "duplicate"

        data = self.load()
        if rule.get("confidence", 0.0) >= 0.90:
            rule = dict(rule)
            rule["auto_approved"] = True
            rule.setdefault("approved_at", datetime.now(UTC).isoformat())
            data["approved"].append(rule)
            self.save(data)
            return "auto_approved"

        data["pending"].append(rule)
        self.save(data)
        return "pending"

    def approve(self, wisdom_id: str) -> dict | None:
        """Move a pending item to approved. Returns the item or None if not found."""
        data = self.load()
        match = next((p for p in data["pending"] if p.get("id") == wisdom_id), None)
        if match is None:
            return None
        data["pending"] = [p for p in data["pending"] if p.get("id") != wisdom_id]
        match["approved_at"] = datetime.now(UTC).isoformat()
        data["approved"].append(match)
        self.save(data)
        return match

    def reject(self, wisdom_id: str) -> bool:
        """Move a pending item to rejected. Returns True if found, False otherwise."""
        data = self.load()
        match = next((p for p in data["pending"] if p.get("id") == wisdom_id), None)
        if match is None:
            return False
        data["pending"] = [p for p in data["pending"] if p.get("id") != wisdom_id]
        match["rejected_at"] = datetime.now(UTC).isoformat()
        data["rejected"].append(match)
        self.save(data)
        return True

    def absorbed_count(self) -> int:
        """Return count of approved rules (used for Mastery Map rank calculation)."""
        return len(self.load().get("approved", []))


# ---------------------------------------------------------------------------
# Z-L encoding helpers for WisdomRules
# ---------------------------------------------------------------------------


def to_zl(rule: dict, aeon_id: str = "AEON") -> str:
    """Encode an approved WisdomRule as a Z-L ASSERT message.

    Format: AEON_ID ! wisdom:rule:<id> [civic:<fingerprint>] [conf:<confidence>] [delta:+1]
    """
    import hashlib
    import re

    rule_id = re.sub(r"[^a-z0-9\-]", "-", rule.get("id", "unknown").lower())[:32]
    confidence = rule.get("confidence", 0.8)

    # Compute fingerprint without civic_hash field (same algorithm as sync.py)
    clean = {k: v for k, v in rule.items() if k != "civic_hash"}
    fingerprint = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(clean, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
    )

    safe_aeon = re.sub(r"[^A-Z0-9_]", "_", aeon_id.upper())[:32]
    if not safe_aeon or not safe_aeon[0].isalpha():
        safe_aeon = "AEON"

    return (
        f"{safe_aeon} ! wisdom:rule:{rule_id}"
        f" [civic:{fingerprint}]"
        f" [conf:{confidence:.2f}]"
        f" [delta:+1]"
    )


def from_zl(zl_str: str) -> dict | None:
    """Parse a Z-L ASSERT message back to a minimal rule dict.

    Returns None if the string is not a valid ASSERT over a wisdom:rule target.
    Does NOT verify the civic hash — caller is responsible for verification.
    """
    try:
        from zana.core.zl_parser import parse as zl_parse

        msg = zl_parse(zl_str)
    except Exception:
        return None

    if msg.verb != "!":
        return None

    if not msg.target.startswith("WISDOM:RULE:"):
        return None

    rule_id = msg.target[len("WISDOM:RULE:") :].lower()
    return {
        "id": rule_id,
        "zl_source": zl_str,
        "confidence": float(msg.modifiers.get("conf", "0.8")),
        "civic": msg.modifiers.get("civic", ""),
    }
