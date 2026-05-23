"""Tests for Z-L (ZANA Language) parser v0.1."""

from __future__ import annotations

import hashlib

import pytest
from zana.core.zl_parser import (
    ZLParseError,
    civic_hash,
    encode,
    parse,
)

# ── Parse: valid messages ─────────────────────────────────────────────────────


def test_parse_minimal():
    msg = parse("ARIA_01 → NEXUS_CORE")
    assert msg.aeon_id == "ARIA_01"
    assert msg.verb == "→"
    assert msg.target == "NEXUS_CORE"
    assert msg.modifiers == {}


def test_parse_with_modifiers():
    msg = parse("ARIA_01 → NEXUS_CORE [context:user_health] [conf:0.92]")
    assert msg.modifiers["context"] == "user_health"
    assert msg.modifiers["conf"] == "0.92"


def test_parse_normalizes_aeon_id_to_uppercase():
    msg = parse("aria_01 → NEXUS_CORE")
    assert msg.aeon_id == "ARIA_01"


def test_parse_normalizes_target_to_uppercase():
    msg = parse("ARIA_01 → nexus_core")
    assert msg.target == "NEXUS_CORE"


def test_parse_ascii_alias_arrow():
    msg = parse("ARIA_01 -> NEXUS_CORE")
    assert msg.verb == "→"


def test_parse_ascii_alias_ok():
    msg = parse("ARIA_01 OK NEXUS_CORE")
    assert msg.verb == "✓"


def test_parse_ascii_alias_no():
    msg = parse("ARIA_01 NO NEXUS_CORE")
    assert msg.verb == "✗"


def test_parse_ascii_alias_escalate():
    msg = parse("ARIA_01 ^ USER:JOHN")
    assert msg.verb == "↑"


def test_parse_delta_modifier():
    msg = parse("GUARDIAN_07 ∂ threat:count [delta:+1]")
    assert msg.modifiers["delta"] == "+1"


def test_parse_civic_chaining():
    msg = parse("ARIA_01 → NEXUS_CORE [civic:sha256:abc123def456]")
    assert msg.modifiers["civic"] == "sha256:abc123def456"


def test_parse_all_verb_symbols():
    verbs = ["→", "?", "!", "~", "∑", "∂", "⊕", "⊗", "↑", "↓", "✓", "✗"]
    extra_mods = {
        "~": " [conf:0.5]",
        "∂": " [delta:+1]",
    }
    for v in verbs:
        text = f"AEON_A {v} TARGET_B" + extra_mods.get(v, "")
        msg = parse(text)
        assert msg.verb == v


# ── Parse: error cases ────────────────────────────────────────────────────────


def test_parse_empty_raises():
    with pytest.raises(ZLParseError, match="Empty"):
        parse("")


def test_parse_missing_target_raises():
    with pytest.raises(ZLParseError, match="requires AEON_ID VERB TARGET"):
        parse("ARIA_01 →")


def test_parse_unknown_verb_raises():
    with pytest.raises(ZLParseError, match="Unknown verb"):
        parse("ARIA_01 UNKNOWN NEXUS_CORE")


def test_parse_invalid_aeon_id_raises():
    with pytest.raises(ZLParseError, match="Invalid AEON_ID"):
        parse("1INVALID → NEXUS_CORE")


def test_parse_invalid_target_raises():
    with pytest.raises(ZLParseError, match="Invalid TARGET"):
        parse("ARIA_01 → target!bang#invalid")


def test_parse_approximate_without_conf_raises():
    with pytest.raises(ZLParseError, match="APPROXIMATE.*conf"):
        parse("ARIA_01 ~ NEXUS_CORE")


def test_parse_delta_without_delta_modifier_raises():
    with pytest.raises(ZLParseError, match="DELTA.*delta"):
        parse("ARIA_01 ∂ NEXUS_CORE")


def test_parse_conf_out_of_range_raises():
    with pytest.raises(ZLParseError, match="conf must be 0.0"):
        parse("ARIA_01 ! NEXUS_CORE [conf:1.5]")


def test_parse_unknown_modifier_key_raises():
    with pytest.raises(ZLParseError, match="Unknown modifier key"):
        parse("ARIA_01 → NEXUS_CORE [unknown:value]")


def test_parse_modifier_missing_value_raises():
    with pytest.raises(ZLParseError, match="Empty value"):
        parse("ARIA_01 → NEXUS_CORE [context:]")


# ── Canonical form and hashing ────────────────────────────────────────────────


def test_canonical_sorts_modifiers():
    msg1 = parse("ARIA_01 → NEXUS_CORE [conf:0.9] [context:health]")
    msg2 = parse("ARIA_01 → NEXUS_CORE [context:health] [conf:0.9]")
    assert msg1.canonical() == msg2.canonical()


def test_civic_hash_is_deterministic():
    msg1 = parse("ARIA_01 → NEXUS_CORE [conf:0.92] [context:user_health]")
    msg2 = parse("ARIA_01 → NEXUS_CORE [context:user_health] [conf:0.92]")
    assert civic_hash(msg1) == civic_hash(msg2)


def test_civic_hash_is_sha256_of_canonical():
    msg = parse("ARIA_01 → NEXUS_CORE [context:test]")
    expected = hashlib.sha256(msg.canonical().encode("utf-8")).hexdigest()
    assert civic_hash(msg) == expected


def test_different_messages_have_different_hashes():
    msg1 = parse("ARIA_01 → NEXUS_CORE")
    msg2 = parse("ARIA_01 → ORACLE_03")
    assert civic_hash(msg1) != civic_hash(msg2)


# ── Encode round-trip ─────────────────────────────────────────────────────────


def test_encode_round_trip():
    original = "ARIA_01 → NEXUS_CORE [conf:0.92] [context:user_health]"
    msg = parse(original)
    encoded = encode(msg)
    reparsed = parse(encoded)
    assert reparsed.aeon_id == msg.aeon_id
    assert reparsed.verb == msg.verb
    assert reparsed.target == msg.target
    assert reparsed.modifiers == msg.modifiers


def test_encode_canonical_is_stable():
    msg = parse("aria_01 -> nexus_core [context:health] [conf:0.9]")
    assert encode(msg) == "ARIA_01 → NEXUS_CORE [conf:0.9] [context:health]"


# ── ZLMessage properties ──────────────────────────────────────────────────────


def test_verb_name_property():
    msg = parse("ARIA_01 → NEXUS_CORE")
    assert msg.verb_name == "TRANSFER"


def test_str_returns_canonical():
    msg = parse("ARIA_01 → NEXUS_CORE [conf:0.5]")
    assert str(msg) == msg.canonical()
