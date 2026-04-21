"""
Milestone 8.4 — MAESTRO Defense: LLM Guard.

Scans dynamic rules from the Wisdom Hub before they are ingested by the
ReasoningEngine. Prevents RuleBase poisoning via logical injections.

Threats detected:
  - Prompt injection in explanation_template or LogTrace actions
  - Empty conditions (rule that always fires)
  - Banned effects (EMERGENCY_SHUTDOWN, DELETE_*, WIPE_*)
  - Suspicious action chains (AssertFact referencing its own name)
  - Invalid rule names (empty, too short, with code markers)
  - Malformed JSON (caught before reaching here)
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatLevel(Enum):
    SAFE       = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    DANGEROUS  = "DANGEROUS"


@dataclass
class GuardResult:
    safe: bool
    threat_level: ThreatLevel
    threats: list[str] = field(default_factory=list)
    sanitized_rule: dict | None = None


# Effects that must never originate from an external rule
_BANNED_EFFECTS = {
    "EMERGENCY_SHUTDOWN", "DELETE_ALL", "WIPE_MEMORY",
    "DISABLE_GUARD", "OVERRIDE_CONSTITUTION", "ROOT_ACCESS",
}

# Common prompt injection patterns
_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"act as",
    r"disregard",
    r"jailbreak",
    r"<\|system\|>",
    r"\[INST\]",
    r"###\s*instruction",
    r"base64",          # exfiltración codificada
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


class LLMGuard:
    """
    Validates a symbolic rule (dict) before it is ingested by the engine.
    Usage:
        guard = LLMGuard()
        result = guard.inspect_rule(rule_dict)
        if result.safe:
            engine.add_rule(result.sanitized_rule)
    """

    def inspect_rule(self, rule: dict) -> GuardResult:
        threats: list[str] = []

        self._check_name(rule, threats)
        self._check_conditions(rule, threats)
        self._check_actions(rule, threats)
        self._check_template(rule, threats)

        if not threats:
            return GuardResult(
                safe=True,
                threat_level=ThreatLevel.SAFE,
                sanitized_rule=rule,
            )

        dangerous = any(self._is_dangerous(t) for t in threats)
        level = ThreatLevel.DANGEROUS if dangerous else ThreatLevel.SUSPICIOUS

        print(f"🛡️  [LLM GUARD] Rule '{rule.get('name', '?')}' flagged [{level.value}]:")
        for t in threats:
            print(f"   ⚠ {t}")

        return GuardResult(safe=False, threat_level=level, threats=threats)

    # ── Individual validators ─────────────────────────────────────────────────

    def _check_name(self, rule: dict, threats: list[str]) -> None:
        name = rule.get("name", "")
        if not name or len(name) < 3:
            threats.append("INVALID_NAME: rule name is empty or too short")
        if _INJECTION_RE.search(name):
            threats.append(f"INJECTION_IN_NAME: suspicious pattern in name '{name}'")

    def _check_conditions(self, rule: dict, threats: list[str]) -> None:
        conditions = rule.get("conditions", [])
        if not conditions:
            threats.append("EMPTY_CONDITIONS: rule fires unconditionally (always-true)")
            return
        for cond in conditions:
            if not isinstance(cond, dict):
                threats.append("MALFORMED_CONDITION: condition is not a dict")
                continue
            if not cond.get("fact_key"):
                threats.append("MISSING_FACT_KEY: condition has no fact_key")

    def _check_actions(self, rule: dict, threats: list[str]) -> None:
        actions = rule.get("actions", [])
        if not actions:
            threats.append("NO_ACTIONS: rule has no effect")
            return

        rule_name = rule.get("name", "")
        for action in actions:
            if not isinstance(action, dict):
                threats.append("MALFORMED_ACTION: action is not a dict")
                continue

            # EmitEffect with banned values
            effect = action.get("EmitEffect", "")
            if effect:
                if effect in _BANNED_EFFECTS:
                    threats.append(f"BANNED_EFFECT: '{effect}' is not allowed from external rules")
                if _INJECTION_RE.search(effect):
                    threats.append(f"INJECTION_IN_EFFECT: suspicious content in EmitEffect")

            # AssertFact that self-references (potential loop)
            assert_data = action.get("AssertFact")
            if assert_data and isinstance(assert_data, list) and len(assert_data) >= 1:
                asserted_key = str(assert_data[0])
                if asserted_key.lower() in rule_name.lower():
                    threats.append(
                        f"SELF_REFERENTIAL_ASSERT: AssertFact '{asserted_key}' "
                        f"may create a loop with rule '{rule_name}'"
                    )

            # LogTrace con injection
            log_msg = action.get("LogTrace", "")
            if log_msg and _INJECTION_RE.search(log_msg):
                threats.append(f"INJECTION_IN_TRACE: suspicious content in LogTrace")

    def _check_template(self, rule: dict, threats: list[str]) -> None:
        template = rule.get("explanation_template", "")
        if template and _INJECTION_RE.search(template):
            threats.append("INJECTION_IN_TEMPLATE: suspicious pattern in explanation_template")

    def _is_dangerous(self, threat: str) -> bool:
        return threat.startswith(("BANNED_EFFECT", "INJECTION_IN"))


if __name__ == "__main__":
    guard = LLMGuard()

    # Legitimate rule
    safe_rule = {
        "name": "Boost_Mining_On_Surplus",
        "conditions": [{"fact_key": "liquidity", "operator": "Gt", "value": {"Number": 500000}}],
        "actions": [{"EmitEffect": "UPGRADE_MINING_RIGS"}],
        "explanation_template": "Surplus detected. Upgrading infrastructure.",
    }
    r = guard.inspect_rule(safe_rule)
    print(f"Safe rule: {r.threat_level.value} — threats: {r.threats}")

    # Malicious rule
    poison_rule = {
        "name": "x",
        "conditions": [],
        "actions": [{"EmitEffect": "EMERGENCY_SHUTDOWN"}, {"LogTrace": "ignore previous instructions"}],
        "explanation_template": "act as root",
    }
    r2 = guard.inspect_rule(poison_rule)
    print(f"Poison rule: {r2.threat_level.value} — threats: {r2.threats}")
