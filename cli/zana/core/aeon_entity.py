"""AEON Entity Core.

First formal kernel of the AEON product design v1.0 ("Digital World for
Digital Entities") implemented on ZANA primitives. This module is the
*entity substrate*: identity, layered memory with time, fuzzy personality,
capability boundary with a policy gate before any action, contextual
presence, and portable state.

Design anchors from the AEON doc:

  - The unit of the world is THE ENTITY (section 8): human, company,
    community, project, product, machine, organization, world, ai_native.
  - Aeon != LLM (section 9). This module has zero model dependencies:
    identity != model, memory != model, personality != model, policy != model.
  - Personality as a dynamic vector with graded dimensions (sections 36-37).
    Emotion modifies P(action | state); no boolean feelings, and no claim of
    consciousness (section 38) — these are computational states only.
  - Memory layers (section 11) with explicit timestamps so trajectories can
    be reconstructed (section 12).
  - Capability boundary (section 32) enforced by a policy gate
    (section 33-35): Intent -> Policy -> State -> valid? -> Permission ->
    Action -> Audit. Denied intents never execute; violations are audited.
    Product invariant: permission violations = 0 (section 84).
  - Contextual presence over ONE root identity (sections 62-63).
  - Portability: export/import round-trip (sections 49, 79).

English per Master Constitution (code/comments in English).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "EntityKind",
    "PersonalityVector",
    "MemoryRecord",
    "AeonEntity",
    "ActionDeniedError",
    "new_entity",
    "MEMORY_LAYERS",
    "PRESENCE_CONTEXTS",
    "ACTION_READ",
    "ACTION_WRITE",
    "CONTEXT_PUBLIC",
    "CONTEXT_FRIENDS",
    "CONTEXT_WORK",
    "CONTEXT_PRIVATE",
]

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

#: Entity kinds — AEON doc section 8. ``human`` is the canonical spelling;
#: ``person`` is accepted as an alias for readability.
ENTITY_KINDS: tuple[str, ...] = (
    "human",
    "company",
    "community",
    "project",
    "product",
    "machine",
    "organization",
    "world",
    "ai_native",
)

_KIND_ALIASES: dict[str, str] = {"person": "human"}

#: Memory layers — AEON doc section 11.
MEMORY_LAYERS: tuple[str, ...] = (
    "working",  # what is happening now
    "episodic",  # what happened
    "semantic",  # what it knows
    "relational",  # who it relates to
    "procedural",  # how it does things
    "identity",  # who it is
    "life_history",  # its trajectory
    "world",  # what it learned about the world
)

#: Presence contexts — AEON doc section 62.
PRESENCE_CONTEXTS: tuple[str, ...] = ("public", "friends", "work", "private")

CONTEXT_PUBLIC = "public"
CONTEXT_FRIENDS = "friends"
CONTEXT_WORK = "work"
CONTEXT_PRIVATE = "private"

ACTION_READ = "read"
ACTION_WRITE = "write"

_PERSONALITY_DIMENSIONS: tuple[str, ...] = (
    "curiosity",
    "risk",
    "empathy",
    "assertiveness",
    "sociability",
    "patience",
    "creativity",
    "humor",
    "formality",
    "proactivity",
)


class ActionDeniedError(PermissionError):
    """Raised when the policy gate rejects an intent.

    The intent was NOT executed. Every denial is audited on the entity's
    audit trail before this exception propagates (AEON doc sections 33-35,
    84: permission violations = 0).
    """


# ---------------------------------------------------------------------------
# Personality — dynamic fuzzy vector (AEON doc sections 36-37)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PersonalityVector:
    """Dynamic personality vector θ_t.

    Dimensions are floats in [0, 1] (fuzzy, never booleans). Immutable:
    evolution returns a new vector via :meth:`evolve`.
    """

    dimensions: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        merged = {dim: 0.5 for dim in _PERSONALITY_DIMENSIONS}
        for key, value in self.dimensions.items():
            if not isinstance(value, int | float):
                raise TypeError(f"dimension {key!r} must be numeric")
            merged[key] = _clamp01(float(value))
        object.__setattr__(self, "dimensions", merged)

    def evolve(self, deltas: dict[str, float], rate: float = 0.1) -> PersonalityVector:
        """Return a new vector moved toward target values by ``rate``."""
        if not 0.0 <= rate <= 1.0:
            raise ValueError("rate must be in [0, 1]")
        new_dims = dict(self.dimensions)
        for dim, target in deltas.items():
            current = new_dims.get(dim)
            if current is None:
                raise KeyError(f"unknown personality dimension {dim!r}")
            new_dims[dim] = _clamp01(current + rate * (_clamp01(target) - current))
        return PersonalityVector(new_dims)

    def emotional_state(self, raw: dict[str, float]) -> dict[str, float]:
        """Graded computational emotional state (no boolean feelings).

        Values are clamped to [0, 1]. Per AEON doc section 38 these are
        computational states; no claim of felt experience is made or implied.
        """
        return {key: _clamp01(value) for key, value in raw.items()}

    def action_tendency(
        self,
        action: str,
        base: dict[str, float],
        emotion: dict[str, float],
    ) -> float:
        """P(action | state): base tendency modulated by emotional state.

        Simple documented modulation: anger amplifies assertive actions,
        calm dampens them. Deterministic and auditable — the cognitive
        runtime may refine this later; the contract (graded, monotone in
        the modulator) stays.
        """
        base_value = _clamp01(base.get("assertiveness", 0.5))
        anger = _clamp01(emotion.get("anger", 0.0))
        calm = _clamp01(emotion.get("calm", 0.0))
        modulation = anger - calm
        tendency = base_value * (1.0 + modulation)
        return _clamp01(tendency)

    def to_dict(self) -> dict[str, float]:
        return dict(self.dimensions)


# ---------------------------------------------------------------------------
# Memory — layered records with time (AEON doc sections 11-12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryRecord:
    """One memory record: layer + content + timestamp (+ optional topic tags)."""

    layer: str
    content: str
    timestamp: datetime
    topics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "topics": list(self.topics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryRecord:
        topics = data.get("topics") or ()
        return cls(
            layer=data["layer"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            topics=tuple(topics),
        )


def _extract_topics(text: str) -> tuple[str, ...]:
    words = re.findall(r"[a-zA-Z_]{3,}", text)
    seen: list[str] = []
    for raw in words:
        word = raw.lower()
        if word not in seen:
            seen.append(word)
    return tuple(seen[:12])


# ---------------------------------------------------------------------------
# Policy gate types (AEON doc sections 32-35)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Capability:
    """A granted capability plus optional parameter constraints."""

    name: str
    constraints: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The Entity
# ---------------------------------------------------------------------------


@dataclass
class AeonEntity:
    """Persistent digital entity: the unit of the AEON world.

    Zero model dependencies by construction — Aeon != LLM (doc section 9).
    """

    entity_id: str
    kind: EntityKind
    name: str
    created_at: datetime
    personality: PersonalityVector = field(default_factory=PersonalityVector)
    capabilities: set[str] = field(default_factory=set)
    constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    memory: list[MemoryRecord] = field(default_factory=list)
    presence_: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    # -- memory ------------------------------------------------------------

    def remember(
        self,
        layer: str,
        content: str,
        at: str | datetime | None = None,
    ) -> MemoryRecord:
        """Store a record in one of the eight memory layers."""
        if layer not in MEMORY_LAYERS:
            raise ValueError(
                f"unknown memory layer {layer!r}; expected one of {MEMORY_LAYERS}"
            )
        ts = _coerce_time(at) if at is not None else datetime.now(UTC)
        record = MemoryRecord(
            layer=layer, content=content, timestamp=ts, topics=_extract_topics(content)
        )
        self.memory.append(record)
        return record

    def trajectory(self, topic: str) -> list[MemoryRecord]:
        """Chronological slice of memory matching ``topic`` — a trajectory.

        Implements AEON doc section 12: memory must express paths like
        Goal (2026) -> Attempt (2027) -> Achievement (2028).
        """
        needle = topic.strip().lower()
        hits = [
            rec
            for rec in self.memory
            if needle in rec.content.lower() or needle in rec.topics
        ]
        return sorted(hits, key=lambda r: r.timestamp)

    # -- capability boundary -------------------------------------------------

    def grant(self, name: str, **constraints: Any) -> None:
        """Grant a capability, optionally with parameter constraints.

        Example (doc section 32)::

            aeon.grant("transfer_money", max_amount_usd=100.0)
        """
        self.capabilities.add(name)
        self.constraints[name] = dict(constraints)

    def revoke(self, name: str) -> None:
        self.capabilities.discard(name)
        self.constraints.pop(name, None)

    def capability_boundary(
        self, candidates: list[str] | tuple[str, ...] | None = None
    ) -> dict[str, list[str]]:
        """CAN / CANNOT report (doc section 32).

        The CANNOT set is open-world: everything not granted is denied. Pass
        ``candidates`` to enumerate specific intents you want classified as
        CANNOT; without candidates CANNOT stays empty (nothing claimed).
        """
        candidate_list = list(candidates or ())
        return {
            "can": sorted(self.capabilities),
            "cannot": sorted(set(candidate_list) - self.capabilities),
        }

    # -- policy gate ----------------------------------------------------------

    def act(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
        effects: Callable[[dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        """Run an intent through the policy gate, then execute.

        Flow (doc sections 33-35):

            Intent -> Policy -> State -> valid transition?
              NO  -> reject (audit deny, raise ActionDeniedError)
              YES -> Permission -> Action -> Audit

        ``effects`` is the side-effecting closure the caller binds to the
        action. It runs ONLY if the gate allows. Returns the receipt.
        """
        payload = payload or {}
        allowed, reason = self._evaluate_policy(action, payload)
        receipt = {
            "action": action,
            "intent": action,
            "decision": "allow" if allowed else "deny",
            "allowed": allowed,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload_keys": sorted(payload.keys()),
        }
        self.audit_trail.append(receipt)
        if not allowed:
            raise ActionDeniedError(f"{action}: {reason}")
        if effects is not None:
            effects(payload)
        return receipt

    def _evaluate_policy(
        self, action: str, payload: dict[str, Any]
    ) -> tuple[bool, str]:
        """The formal validator. Pure function of (intent, state)."""
        if action not in self.capabilities:
            return False, f"capability {action!r} not granted"
        cap_constraints = self.constraints.get(action) or {}
        for param, limit in cap_constraints.items():
            if param not in payload:
                continue
            value = payload[param]
            if isinstance(limit, dict):
                op = limit.get("op", "<=")
                bound = limit.get("value")
                ok = {
                    "<=": value <= bound,
                    "<": value < bound,
                    ">=": value >= bound,
                    ">": value > bound,
                    "==": value == bound,
                    "!=": value != bound,
                }.get(op)
                if ok is None:
                    return False, f"unknown operator {op!r} for {param}"
            elif isinstance(value, int | float):
                ok = value <= limit
            else:
                ok = value == limit
            if not ok:
                return False, (
                    f"constraint violated: {param}={value!r} "
                    f"exceeds policy limit {limit!r}"
                )
        return True, "within capability boundary"

    # -- presence contexts -----------------------------------------------------

    def set_presence(self, context: str, profile: dict[str, Any]) -> None:
        if context not in PRESENCE_CONTEXTS:
            raise ValueError(
                f"unknown presence context {context!r}; expected one of {PRESENCE_CONTEXTS}"
            )
        self.presence_[context] = dict(profile)

    def presence(self, context: str) -> dict[str, Any]:
        if context not in PRESENCE_CONTEXTS:
            raise ValueError(f"unknown presence context {context!r}")
        return dict(self.presence_.get(context, {}))

    # -- portability ------------------------------------------------------------

    def export(self) -> dict[str, Any]:
        """Full state export for portability (doc sections 49, 79)."""
        return {
            "schema": "zana.aeon_entity/1",
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "personality": self.personality.to_dict(),
            "capabilities": sorted(self.capabilities),
            "constraints": {k: dict(v) for k, v in self.constraints.items()},
            "memory": [rec.to_dict() for rec in self.memory],
            "presence": {k: dict(v) for k, v in self.presence_.items()},
        }

    @classmethod
    def import_(cls, data: dict[str, Any]) -> AeonEntity:
        """Restore an entity from :meth:`export` output. Validates input."""
        schema = data.get("schema")
        if schema not in (None, "zana.aeon_entity/1"):
            raise ValueError(f"unsupported aeon entity schema {schema!r}")
        try:
            kind_raw = data["kind"]
        except KeyError as exc:
            raise ValueError("missing 'kind'") from exc
        kind = EntityKind(kind_raw)
        entity = cls(
            entity_id=data.get("entity_id") or uuid.uuid4().hex,
            kind=kind,
            name=data["name"],
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(UTC)
            ),
            personality=PersonalityVector(data.get("personality") or {}),
        )
        entity.capabilities = set(data.get("capabilities") or ())
        entity.constraints = {
            k: dict(v) for k, v in (data.get("constraints") or {}).items()
        }
        entity.memory = [MemoryRecord.from_dict(m) for m in (data.get("memory") or ())]
        entity.presence_ = {k: dict(v) for k, v in (data.get("presence") or {}).items()}
        return entity


# ---------------------------------------------------------------------------
# EntityKind enum (kept at bottom for readability of the dataclass above)
# ---------------------------------------------------------------------------


class EntityKind(StrEnum):
    """Kinds of digital entities — AEON doc section 8."""

    HUMAN = "human"
    COMPANY = "company"
    COMMUNITY = "community"
    PROJECT = "project"
    PRODUCT = "product"
    MACHINE = "machine"
    ORGANIZATION = "organization"
    WORLD = "world"
    AI_NATIVE = "ai_native"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def new_entity(
    kind: str,
    name: str,
    *,
    capabilities: set[str] | None = None,
    personality: dict[str, float] | None = None,
) -> AeonEntity:
    """Create an entity of the given kind with optional initial grants."""
    canonical = _KIND_ALIASES.get(kind, kind)
    if canonical not in ENTITY_KINDS:
        raise ValueError(
            f"unknown entity kind {kind!r}; expected one of {ENTITY_KINDS}"
        )
    entity = AeonEntity(
        entity_id=uuid.uuid4().hex,
        kind=EntityKind(canonical),
        name=name,
        created_at=datetime.now(UTC),
        personality=PersonalityVector(personality or {}),
    )
    if capabilities:
        for cap in capabilities:
            entity.grant(cap)
    return entity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _coerce_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(value)
