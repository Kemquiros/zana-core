"""
zl_parser.py — Z-L (ZANA Language) parser v0.1

Z-L is a symbolic protocol for Aeon-to-Aeon cognitive coordination.
Message structure: ⟨AEON_ID⟩ ⟨VERB⟩ ⟨TARGET⟩ [modifier ...]

Security: canonical form is deterministic → SHA-256 civic hash is reproducible.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# ── Verb catalog ──────────────────────────────────────────────────────────────

VERB_SYMBOLS: frozenset[str] = frozenset(
    ["→", "?", "!", "~", "∑", "∂", "⊕", "⊗", "↑", "↓", "✓", "✗"]
)

# ASCII aliases accepted in input, normalized to Unicode on parse
_ASCII_ALIASES: dict[str, str] = {
    "->": "→",
    "SUM": "∑",
    "DELTA": "∂",
    "MERGE": "⊕",
    "CONFLICT": "⊗",
    "^": "↑",
    "v": "↓",
    "OK": "✓",
    "NO": "✗",
}

VERB_NAMES: dict[str, str] = {
    "→": "TRANSFER",
    "?": "QUERY",
    "!": "ASSERT",
    "~": "APPROXIMATE",
    "∑": "AGGREGATE",
    "∂": "DELTA",
    "⊕": "MERGE",
    "⊗": "CONFLICT",
    "↑": "ESCALATE",
    "↓": "DELEGATE",
    "✓": "CONFIRM",
    "✗": "REJECT",
}

# ── Validation patterns ───────────────────────────────────────────────────────

_AEON_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_TARGET_RE = re.compile(r"^[A-Za-z0-9_.:/\-]{1,64}$")
_MODIFIER_RE = re.compile(r"\[([^\]]+)\]")
_VALID_MODIFIER_KEYS = frozenset(
    ["context", "conf", "delta", "civic", "payload", "ttl"]
)


# ── ZLMessage dataclass ───────────────────────────────────────────────────────


@dataclass
class ZLMessage:
    aeon_id: str
    verb: str
    target: str
    modifiers: dict[str, str] = field(default_factory=dict)

    @property
    def verb_name(self) -> str:
        return VERB_NAMES.get(self.verb, "UNKNOWN")

    def canonical(self) -> str:
        """Return the canonical form used for hashing (modifiers sorted by key)."""
        base = f"{self.aeon_id.upper()} {self.verb} {self.target.upper()}"
        if not self.modifiers:
            return base
        mods = " ".join(f"[{k}:{v}]" for k, v in sorted(self.modifiers.items()))
        return f"{base} {mods}"

    def civic_hash(self) -> str:
        """SHA-256 of the canonical form — the Z-L Civic Hash."""
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        return self.canonical()


# ── Parser ────────────────────────────────────────────────────────────────────


class ZLParseError(ValueError):
    """Raised when a Z-L message cannot be parsed."""


def _normalize_verb(raw: str) -> str:
    """Resolve ASCII alias or validate Unicode glyph."""
    if raw in VERB_SYMBOLS:
        return raw
    if raw in _ASCII_ALIASES:
        return _ASCII_ALIASES[raw]
    raise ZLParseError(f"Unknown verb: {raw!r}. Valid: {sorted(VERB_SYMBOLS)}")


def parse(text: str, *, record: bool = False) -> ZLMessage:
    """Parse a Z-L message string into a ZLMessage.

    Args:
        text: The raw Z-L message string.
        record: If True, write the parsed message to the Civic Ledger.

    Raises:
        ZLParseError: If the message is malformed.
    """
    text = text.strip()
    if not text:
        raise ZLParseError("Empty Z-L message")

    # Extract modifiers first (bracketed), leaving the core tokens
    modifiers: dict[str, str] = {}
    modifier_matches = _MODIFIER_RE.findall(text)
    for m in modifier_matches:
        if ":" not in m:
            raise ZLParseError(f"Malformed modifier (missing ':'): [{m}]")
        key, _, value = m.partition(":")
        key = key.strip()
        value = value.strip()
        if key not in _VALID_MODIFIER_KEYS:
            raise ZLParseError(
                f"Unknown modifier key: {key!r}. Valid: {sorted(_VALID_MODIFIER_KEYS)}"
            )
        if not value:
            raise ZLParseError(f"Empty value for modifier: {key}")
        modifiers[key] = value

    core = _MODIFIER_RE.sub("", text).strip()
    tokens = core.split()

    if len(tokens) < 3:
        raise ZLParseError(
            f"Z-L message requires AEON_ID VERB TARGET, got {len(tokens)} token(s): {core!r}"
        )

    aeon_id, raw_verb, target = tokens[0], tokens[1], tokens[2]

    # Validate AEON_ID
    if not _AEON_ID_RE.match(aeon_id.upper()):
        raise ZLParseError(
            f"Invalid AEON_ID {aeon_id!r}. Must match [A-Z][A-Z0-9_]{{1,31}}"
        )

    # Normalize and validate VERB
    verb = _normalize_verb(raw_verb)

    # Validate TARGET
    if not _TARGET_RE.match(target):
        raise ZLParseError(
            f"Invalid TARGET {target!r}. Must match [A-Za-z0-9_.:/\\-]{{1,64}}"
        )

    # Semantic validation: ~ (APPROXIMATE) requires conf:
    if verb == "~" and "conf" not in modifiers:
        raise ZLParseError("APPROXIMATE (~) requires [conf:⟨0-1⟩] modifier")

    # Semantic validation: ∂ (DELTA) requires delta:
    if verb == "∂" and "delta" not in modifiers:
        raise ZLParseError("DELTA (∂) requires [delta:⟨±N⟩] modifier")

    # Validate conf range if present
    if "conf" in modifiers:
        raw_conf = modifiers["conf"]
        try:
            conf_val = float(raw_conf)
        except ValueError:
            raise ZLParseError(f"conf must be a float, got {raw_conf!r}") from None
        if not 0.0 <= conf_val <= 1.0:
            raise ZLParseError(f"conf must be 0.0–1.0, got {conf_val}")

    msg = ZLMessage(
        aeon_id=aeon_id.upper(),
        verb=verb,
        target=target.upper(),
        modifiers=modifiers,
    )

    if record:
        _record_to_ledger(msg)

    return msg


def encode(msg: ZLMessage) -> str:
    """Serialize a ZLMessage back to its canonical Z-L string."""
    return msg.canonical()


def civic_hash(msg: ZLMessage) -> str:
    """Return the SHA-256 civic hash of the message's canonical form."""
    return msg.civic_hash()


# ── Civic Ledger integration ──────────────────────────────────────────────────


def _record_to_ledger(msg: ZLMessage) -> None:
    """Write a parsed Z-L message to SentinelLiteDB (best-effort)."""
    try:
        from zana.core.sentinel_lite import SentinelLiteDB

        db = SentinelLiteDB()
        db.record(
            f"ZL:{msg.verb_name}",
            payload_hash=msg.civic_hash(),
            civic_hash=msg.civic_hash(),
        )
        db.close()
    except Exception:
        pass
