"""AEON Entity Core — tests.

Covers the AEON Product Design v1.0 slice implemented in
zana/core/aeon_entity.py:

  - Entity kinds (persona, empresa, comunidad, proyecto, producto, maquina,
    organizacion, mundo, ai_native) — doc section 8.
  - Personality as a dynamic vector of fuzzy dimensions in [0, 1] — sections
    36-37. No boolean emotions; graded states that modulate action tendency.
  - Memory with time: layered records (working/episodic/semantic/relational/
    procedural/identity/life_history/world) with timestamps and trajectory
    reconstruction — sections 11-12.
  - Policy gate before any action: Intent -> Policy -> State -> valid
    transition? -> Permission -> Action -> Audit — sections 32-35.
    The LLM proposes; the formal system validates.
  - Capability boundary: CAN / CANNOT enforced mechanically, violations
    audited, permission violations = 0 as product metric — section 84.
  - Presence contexts (public/friends/work/private) — section 62.
  - Portability: export/import round-trip of the full entity state —
    sections 49, 79.

All tests use tmp_path isolation — zero writes to real ~/.zana/.
"""

from __future__ import annotations

import contextlib
import json

import pytest
from zana.core.aeon_entity import (
    ACTION_READ,
    ACTION_WRITE,
    CONTEXT_PRIVATE,
    CONTEXT_PUBLIC,
    ActionDeniedError,
    AeonEntity,
    EntityKind,
    PersonalityVector,
    new_entity,
)

# ---------------------------------------------------------------------------
# Entity creation and kinds (doc section 8)
# ---------------------------------------------------------------------------


class TestEntityCreation:
    def test_creates_human_entity_with_identity(self):
        aeon = new_entity(kind="human", name="John")
        assert isinstance(aeon, AeonEntity)
        assert aeon.kind is EntityKind.HUMAN
        assert aeon.name == "John"
        assert aeon.entity_id  # non-empty unique id

    @pytest.mark.parametrize(
        "kind",
        [
            "human",
            "company",
            "community",
            "project",
            "product",
            "machine",
            "organization",
            "world",
            "ai_native",
        ],
    )
    def test_all_entity_kinds_exist(self, kind):
        aeon = new_entity(kind=kind, name="x")
        assert aeon.kind.value == kind

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError):
            new_entity(kind="corporation", name="x")

    def test_ids_are_unique(self):
        a = new_entity(kind="human", name="a")
        b = new_entity(kind="human", name="b")
        assert a.entity_id != b.entity_id


# ---------------------------------------------------------------------------
# Personality as fuzzy dynamic vector (doc sections 36-37)
# ---------------------------------------------------------------------------


class TestPersonalityVector:
    def test_default_personality_has_canonical_dimensions(self):
        p = PersonalityVector()
        for dim in (
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
        ):
            assert dim in p.dimensions

    def test_dimensions_are_floats_in_unit_interval(self):
        p = PersonalityVector({"curiosity": 0.7})
        value = p.dimensions["curiosity"]
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_out_of_range_value_clamped_not_raised(self):
        p = PersonalityVector({"risk": 1.7, "empathy": -0.5})
        assert p.dimensions["risk"] == 1.0
        assert p.dimensions["empathy"] == 0.0

    def test_evolve_moves_toward_target(self):
        p = PersonalityVector({"patience": 0.2})
        evolved = p.evolve({"patience": 0.8}, rate=0.5)
        assert evolved.dimensions["patience"] == pytest.approx(0.5)

    def test_evolve_is_immutable(self):
        p = PersonalityVector({"patience": 0.2})
        p.evolve({"patience": 0.9}, rate=0.9)
        assert p.dimensions["patience"] == 0.2  # original untouched

    def test_emotional_state_is_graded_not_boolean(self):
        # Doc section 37: not Angry=true but Anger=0.67.
        p = PersonalityVector()
        state = p.emotional_state({"anger": 0.67, "frustration": 0.81, "calm": 0.23})
        assert state["anger"] == pytest.approx(0.67)
        assert isinstance(state["frustration"], float)

    def test_action_tendency_modulated_by_emotion(self):
        calm = PersonalityVector().emotional_state({"calm": 0.9, "anger": 0.05})
        angry = PersonalityVector().emotional_state({"calm": 0.05, "anger": 0.95})
        base = {"assertiveness": 0.5}
        t_calm = PersonalityVector().action_tendency("publish", base, calm)
        t_angry = PersonalityVector().action_tendency("publish", base, angry)
        # Emotion modifies P(action | state): anger raises assertive actions.
        assert t_angry > t_calm


# ---------------------------------------------------------------------------
# Layered memory with time and trajectories (doc sections 11-12)
# ---------------------------------------------------------------------------


class TestMemory:
    def test_memory_layers_supported(self):
        aeon = new_entity(kind="human", name="J")
        for layer in (
            "working",
            "episodic",
            "semantic",
            "relational",
            "procedural",
            "identity",
            "life_history",
            "world",
        ):
            aeon.remember(layer=layer, content=f"{layer} fact")
        assert len(aeon.memory) == 8

    def test_invalid_layer_rejected(self):
        aeon = new_entity(kind="human", name="J")
        with pytest.raises(ValueError):
            aeon.remember(layer="short_term", content="x")

    def test_memory_records_have_timestamps(self):
        aeon = new_entity(kind="human", name="J")
        aeon.remember(layer="episodic", content="said X")
        record = aeon.memory[0]
        assert record.timestamp is not None

    def test_trajectory_reconstruction(self):
        # Doc section 12: memory must understand trajectories over years.
        aeon = new_entity(kind="human", name="J")
        aeon.remember(
            layer="life_history",
            content="Goal: launch product",
            at="2026-01-01T00:00:00+00:00",
        )
        aeon.remember(
            layer="life_history",
            content="Attempted product strategy Y",
            at="2026-06-01T00:00:00+00:00",
        )
        aeon.remember(
            layer="life_history",
            content="Achieved product milestone Z",
            at="2027-02-01T00:00:00+00:00",
        )
        traj = aeon.trajectory(topic="product")
        assert len(traj) == 3
        moments = [t.content for t in traj]
        assert any("Goal" in m for m in moments)
        assert any("Achieved" in m for m in moments)

    def test_trajectory_ordered_by_time(self):
        aeon = new_entity(kind="human", name="J")
        aeon.remember(layer="episodic", content="later event", at="2027-01-01T00:00:00+00:00")
        aeon.remember(layer="episodic", content="earlier event", at="2026-01-01T00:00:00+00:00")
        traj = aeon.trajectory(topic="event")
        assert traj[0].content == "earlier event"
        assert traj[-1].content == "later event"


# ---------------------------------------------------------------------------
# Capability boundary + policy gate (doc sections 32-35, 84)
# ---------------------------------------------------------------------------


class TestPolicyGate:
    def _entity(self) -> AeonEntity:
        return new_entity(
            kind="human",
            name="J",
            capabilities={"read_calendar", "schedule_meeting"},
        )

    def test_allowed_action_executes_and_audits(self):
        aeon = self._entity()
        receipt = aeon.act(action="read_calendar", payload={"day": "monday"})
        assert receipt["allowed"] is True
        assert receipt["action"] == "read_calendar"
        # Every authorized action leaves an audit trail.
        audits = [e for e in aeon.audit_trail if e["intent"] == "read_calendar"]
        assert len(audits) == 1
        assert audits[0]["decision"] == "allow"

    def test_denied_action_raises_and_audits_violation(self):
        aeon = self._entity()
        with pytest.raises(ActionDeniedError):
            aeon.act(action="transfer_money", payload={"amount_usd": 999})
        # Permission violation attempts are audited, never silent.
        audits = [e for e in aeon.audit_trail if e["intent"] == "transfer_money"]
        assert len(audits) == 1
        assert audits[0]["decision"] == "deny"

    def test_unknown_action_denied_by_default(self):
        aeon = self._entity()
        with pytest.raises(ActionDeniedError):
            aeon.act(action="delete_account", payload={})

    def test_policy_can_add_contextual_constraint(self):
        aeon = self._entity()
        # CAN transfer money only below threshold (doc section 32). The
        # constraint kwarg names the payload parameter it bounds.
        aeon.grant("transfer_money", amount_usd={"op": "<=", "value": 100.0})
        with pytest.raises(ActionDeniedError):
            aeon.act(action="transfer_money", payload={"amount_usd": 250.0})
        receipt = aeon.act(action="transfer_money", payload={"amount_usd": 50.0})
        assert receipt["allowed"] is True

    def test_revoke_removes_capability(self):
        aeon = self._entity()
        aeon.revoke("read_calendar")
        with pytest.raises(ActionDeniedError):
            aeon.act(action="read_calendar", payload={})

    def test_zero_permission_violations_invariant(self):
        # Doc section 84: permission violations = 0. Denied means NOT executed:
        # we assert no denied intent ever produced an executed effect.
        aeon = self._entity()
        executed = []
        try:
            aeon.act(
                action="read_calendar",
                payload={"day": "monday"},
                effects=lambda p: executed.append(p),
            )
            aeon.act(
                action="sign_contract",
                payload={"contract": "x"},
                effects=lambda p: executed.append(p),
            )
        except ActionDeniedError:
            pass
        assert executed == [{"day": "monday"}]  # only the allowed one ran

    def test_boundary_report_shows_can_and_cannot(self):
        aeon = self._entity()
        report = aeon.capability_boundary()
        assert "read_calendar" in report["can"]
        # Open world: CANNOT is computed against candidate intents.
        report = aeon.capability_boundary(candidates=["transfer_money"])
        assert "transfer_money" in report["cannot"]

    def test_audit_trail_is_chronological_with_reasons(self):
        aeon = self._entity()
        aeon.act(action="read_calendar", payload={})
        with contextlib.suppress(ActionDeniedError):
            aeon.act(action="unknown_thing", payload={})
        decisions = [e["decision"] for e in aeon.audit_trail]
        assert decisions == ["allow", "deny"]
        assert all(e.get("reason") for e in aeon.audit_trail)


# ---------------------------------------------------------------------------
# Presence contexts (doc section 62)
# ---------------------------------------------------------------------------


class TestPresenceContexts:
    def test_presence_profile_per_context(self):
        aeon = new_entity(kind="human", name="J")
        aeon.set_presence(
            CONTEXT_PUBLIC,
            {"bio": "builder", "interests": ["ai", "math"]},
        )
        aeon.set_presence(CONTEXT_PRIVATE, {"bio": ""})
        assert aeon.presence(CONTEXT_PUBLIC)["bio"] == "builder"
        assert aeon.presence(CONTEXT_PRIVATE)["bio"] == ""

    def test_unknown_context_rejected(self):
        aeon = new_entity(kind="human", name="J")
        with pytest.raises(ValueError):
            aeon.set_presence("secret", {"bio": "x"})

    def test_root_identity_single_not_fragmented(self):
        # Doc section 63: contextual presences exist but ONE root identity.
        aeon = new_entity(kind="human", name="J")
        aeon.set_presence(CONTEXT_PUBLIC, {"bio": "a"})
        aeon.set_presence(CONTEXT_PRIVATE, {"bio": "b"})
        assert aeon.name == "J"  # single root identity persists


# ---------------------------------------------------------------------------
# Portability (doc sections 49, 79)
# ---------------------------------------------------------------------------


class TestPortability:
    def test_export_import_round_trip(self):
        original = new_entity(kind="human", name="J", capabilities={"read_calendar"})
        original.remember(layer="episodic", content="first fact")
        original.set_presence(CONTEXT_PUBLIC, {"bio": "builder"})

        blob = json.dumps(original.export())

        restored = AeonEntity.import_(json.loads(blob))
        assert restored.entity_id == original.entity_id
        assert restored.name == original.name
        assert restored.kind is original.kind
        assert restored.memory[0].content == "first fact"
        assert "read_calendar" in restored.capabilities
        assert restored.personality.dimensions == original.personality.dimensions
        assert restored.presence(CONTEXT_PUBLIC)["bio"] == "builder"

    def test_export_excludes_audit_trail_opt_in(self):
        # Audit trail is runtime-local evidence; identity port carries state.
        aeon = new_entity(kind="human", name="J")
        blob = aeon.export()
        assert "audit_trail" not in blob

    def test_import_validates_kind(self):
        with pytest.raises(ValueError):
            AeonEntity.import_({"kind": "alien", "name": "x"})


# ---------------------------------------------------------------------------
# Shared read/write constants used by callers
# ---------------------------------------------------------------------------


def test_constants_exported():
    assert ACTION_READ == "read"
    assert ACTION_WRITE == "write"
