"""
/reason — Forward-chaining reasoning endpoint.

Python mirror of reasoning_engine/src/lib.rs — same rules, same operator set.
When zana_steel_core exposes PyO3 bindings for the engine, swap _PyReasoningEngine
for the Rust version and delete this file.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("zana.reason")

router = APIRouter(prefix="/reason", tags=["Reasoning"])

REGISTRY_URL = os.getenv("ZANA_REGISTRY_URL", "http://localhost:54445")


# ── Python mirror of Rust types ───────────────────────────────────────────────


def _coerce(raw: Any) -> Any:
    """JSON value → typed FactValue-compatible Python primitive."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


class _Condition:
    def __init__(
        self, fact_key: str, operator: str, value: Any, field_path: str | None = None
    ):
        self.fact_key = fact_key
        self.operator = operator.lower()
        self.value = _coerce(value)
        self.field_path = field_path

    def matches(self, kb: dict[str, Any]) -> bool:
        raw = kb.get(self.fact_key)
        if raw is None:
            return False
        v = (
            raw.get(self.field_path)
            if self.field_path and isinstance(raw, dict)
            else raw
        )
        v = _coerce(v)
        cmp = self.value
        match self.operator:
            case "eq":
                return v == cmp
            case "neq":
                return v != cmp
            case "gt":
                return isinstance(v, float) and isinstance(cmp, float) and v > cmp
            case "lt":
                return isinstance(v, float) and isinstance(cmp, float) and v < cmp
            case "gte":
                return isinstance(v, float) and isinstance(cmp, float) and v >= cmp
            case "lte":
                return isinstance(v, float) and isinstance(cmp, float) and v <= cmp
            case "contains":
                return isinstance(v, str) and isinstance(cmp, str) and cmp in v
            case _:
                return False


class _Rule:
    def __init__(
        self,
        name: str,
        conditions: list[_Condition],
        effects: list[str],
        explanation: str,
        confidence: float = 0.9,
    ):
        self.name = name
        self.conditions = conditions
        self.effects = effects
        self.explanation = explanation
        self.confidence = confidence


class _PyReasoningEngine:
    """Stateless forward-chaining engine — mirrors Rust ReasoningEngine logic."""

    DEFAULT_RULES: list[_Rule] = [
        _Rule(
            "Empire_Survival_v2",
            [
                _Condition("machine_health_avg", "lt", 0.4),
                _Condition("liquidity", "lt", 50000.0),
            ],
            ["LOCK_EXPENSES"],
            "Salud industrial ({machine_health_avg}) crítica y liquidez ({liquidity}) insuficiente → Protocolo de Austeridad.",
            confidence=0.95,
        ),
        _Rule(
            "Wisdom_Threshold",
            [_Condition("active_peers", "gte", 5.0)],
            ["SYNC_COMMUNITY_RULES"],
            "Enjambre de {active_peers} nodos detectado → Sincronizando sabiduría comunitaria.",
            confidence=0.85,
        ),
        _Rule(
            "Self_Critique_Pattern",
            [_Condition("last_action_status", "eq", "FAILED")],
            ["TRIGGER_REPLANNING"],
            "Falla en acción previa detectada → Iniciando bucle de reflexión.",
            confidence=0.90,
        ),
        _Rule(
            "High_Surprise_Alert",
            [_Condition("kalman_surprise", "gt", 2.0)],
            ["ELEVATE_ATTENTION"],
            "Sorpresa Kalman ({kalman_surprise:.2f}) por encima del umbral → Modo atención elevada.",
            confidence=0.80,
        ),
        _Rule(
            "Low_ZFI_Recovery",
            [_Condition("zfi_score", "lt", 60.0)],
            ["RESTART_CRITICAL_SERVICES"],
            "ZFI ({zfi_score}/100) crítico → Reinicio de servicios esenciales recomendado.",
            confidence=0.92,
        ),
    ]

    def infer(
        self, facts: dict[str, Any], extra_rules: list[dict] | None = None
    ) -> dict:
        kb = {k: _coerce(v) for k, v in facts.items()}
        rules = list(self.DEFAULT_RULES)

        # Swarm rules injected dynamically
        if extra_rules:
            for rd in extra_rules:
                try:
                    conds = [
                        _Condition(
                            c["fact_key"],
                            c.get("operator", "eq"),
                            c["value"],
                            c.get("field_path"),
                        )
                        for c in rd.get("conditions", [])
                    ]
                    rules.append(
                        _Rule(
                            rd.get("name", "swarm_rule"),
                            conds,
                            rd.get("effects", []),
                            rd.get("explanation", "Swarm rule triggered."),
                            rd.get("confidence", 0.75),
                        )
                    )
                except Exception:
                    pass

        deductions = []
        trace = []
        all_effects: list[str] = []

        for rule in rules:
            if all(c.matches(kb) for c in rule.conditions):
                explanation = rule.explanation
                try:
                    explanation = explanation.format(
                        **{
                            k: round(v, 3) if isinstance(v, float) else v
                            for k, v in kb.items()
                        }
                    )
                except Exception:
                    pass

                deductions.append(
                    {
                        "rule": rule.name,
                        "conclusion": explanation,
                        "action": ", ".join(rule.effects),
                        "confidence": rule.confidence,
                    }
                )
                trace.append(
                    {
                        "rule": rule.name,
                        "action": ", ".join(rule.effects),
                        "confidence": rule.confidence,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                all_effects.extend(rule.effects)
                logger.info("🧠 [REASON] %s → %s", rule.name, rule.effects)

        return {
            "facts_asserted": facts,
            "deductions": deductions,
            "effects": list(set(all_effects)),
            "trace": trace,
            "rules_evaluated": len(rules),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


_engine = _PyReasoningEngine()


# ── Request/Response models ───────────────────────────────────────────────────


class ReasonRequest(BaseModel):
    fact: dict[str, Any]
    remote_query: bool = False


class MultiFactRequest(BaseModel):
    facts: dict[str, Any]
    remote_query: bool = False


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", summary="Assert a fact and trigger forward-chaining")
async def reason_single(req: ReasonRequest):
    """
    Asserts one fact (key + value) into the reasoning engine and runs
    all rules in one forward-chaining pass.

    With remote_query=true, escalates to the Wisdom Hub Registry if no
    local rules fire for the given fact.
    """
    fact_key = req.fact.get("fact_key") or next(iter(req.fact), None)
    fact_val = req.fact.get("value", req.fact.get(fact_key))

    if fact_key is None:
        return {"error": "fact_key required"}

    facts = {fact_key: fact_val}
    swarm_rules: list[dict] = []
    swarm_rule_meta: dict | None = None

    result = _engine.infer(facts, swarm_rules)

    # If nothing fired locally and remote_query requested → ask swarm
    if req.remote_query and not result["deductions"]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{REGISTRY_URL}/wisdom")
                if resp.status_code == 200:
                    all_rules = resp.json()
                    # Filter rules that mention this fact_key
                    swarm_rules = [
                        r["rule_data"]
                        for r in all_rules
                        if any(
                            c.get("fact_key") == fact_key
                            for c in r.get("rule_data", {}).get("conditions", [])
                        )
                    ]
                    if swarm_rules:
                        best_raw = max(all_rules, key=lambda r: r.get("votes", 0))
                        swarm_rule_meta = {
                            "name": best_raw.get("rule_data", {}).get(
                                "name", best_raw.get("id", "?")
                            ),
                            "creator_node": best_raw.get("creator_node", "?"),
                            "votes": best_raw.get("votes", 0),
                        }
                        result = _engine.infer(facts, swarm_rules)
        except Exception as e:
            logger.warning("Remote query failed: %s", e)

    if swarm_rule_meta:
        result["swarm_rule"] = swarm_rule_meta

    return result


@router.post("/batch", summary="Assert multiple facts at once")
async def reason_batch(req: MultiFactRequest):
    """Assert multiple facts simultaneously — all rules evaluated against the full KB."""
    swarm_rules: list[dict] = []

    result = _engine.infer(req.facts, swarm_rules)

    if req.remote_query and not result["deductions"]:
        # Same swarm escalation as single-fact endpoint
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{REGISTRY_URL}/wisdom")
                if resp.status_code == 200:
                    swarm_rules = [r["rule_data"] for r in resp.json()]
                    result = _engine.infer(req.facts, swarm_rules)
        except Exception:
            pass

    return result


@router.get("/rules", summary="List all active reasoning rules")
async def list_rules():
    """Returns all default rules loaded in the engine."""
    return {
        "rules": [
            {
                "name": r.name,
                "conditions": [
                    {
                        "fact_key": c.fact_key,
                        "operator": c.operator,
                        "value": c.value,
                        "field_path": c.field_path,
                    }
                    for c in r.conditions
                ],
                "effects": r.effects,
                "confidence": r.confidence,
            }
            for r in _engine.DEFAULT_RULES
        ],
        "total": len(_engine.DEFAULT_RULES),
    }
