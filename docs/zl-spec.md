# Z-L (ZANA Language) — Specification v0.1

> *A symbolic protocol for Aeon-to-Aeon cognitive coordination.*

---

## 1. Purpose

Z-L is a minimal symbolic language for communication between ZANA Aeons within a
Z-Network swarm. It is **not** a general-purpose programming language. It is a
**protocol of cognitive intent** — a compact, hash-able vocabulary for the things
Aeons do to each other: query, assert, transfer, delegate, escalate, confirm, reject.

### Why not natural language?

Natural language is verbose, ambiguous, and language-specific. An Aeon expressing
intent in Spanish and one in English cannot reliably interoperate at the protocol
layer without translation overhead.

### Why not JSON?

JSON is structurally rich but semantically opaque. `{"type": "transfer", "data": ...}`
requires schema negotiation; it carries no inherent cognitive meaning. Z-L assigns
semantic weight to every token.

### Design goals

| Goal | Mechanism |
|------|-----------|
| **Hash-able** | Any Z-L expression has a canonical form → deterministic SHA-256 |
| **Language-agnostic** | Verb symbols are Unicode glyphs, not keywords |
| **Minimal** | 12 primitive verbs cover all coordination semantics |
| **Auditable** | Z-L messages are first-class Civic Ledger entries |
| **Composable** | Messages chain via `[civic:sha256:⟨prev⟩]` into tamper-evident threads |

---

## 2. Message Structure

```
⟨AEON_ID⟩ ⟨VERB⟩ ⟨TARGET⟩ [⟨modifier⟩ ...]
```

### 2.1 Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| `AEON_ID` | Yes | `[A-Z0-9_]{2,32}` | `ARIA_01` |
| `VERB` | Yes | One of 12 glyph symbols | `→` |
| `TARGET` | Yes | `[A-Z0-9_.:/-]{1,64}` | `NEXUS_CORE` or `memory:episodic` |
| Modifiers | No | `key:value` pairs | `[conf:0.92]` |

### 2.2 Modifiers

| Modifier | Type | Meaning |
|----------|------|---------|
| `context:⟨str⟩` | string | semantic context of the message |
| `conf:⟨float⟩` | 0.0–1.0 | confidence / certainty of the assertion |
| `delta:⟨±int⟩` | integer | magnitude of state change |
| `civic:sha256:⟨hex⟩` | 64-char hex | SHA-256 of a prior message (chaining) |
| `payload:⟨str⟩` | string | compact data payload (max 256 chars) |
| `ttl:⟨int⟩` | seconds | time-to-live before message expires |

### 2.3 Grammar (EBNF)

```ebnf
message    = aeon_id SP verb SP target { SP modifier } ;
aeon_id    = [A-Z][A-Z0-9_]* ;
verb       = "→" | "?" | "!" | "~" | "∑" | "∂" | "⊕" | "⊗" | "↑" | "↓" | "✓" | "✗" ;
target     = [A-Za-z0-9_.:/-]+ ;
modifier   = "[" key ":" value "]" ;
key        = "context" | "conf" | "delta" | "civic" | "payload" | "ttl" ;
value      = [^\]]+ ;
SP         = " " ;
```

---

## 3. Verb Catalog

| Symbol | ASCII alias | Verb | Cognitive meaning |
|--------|-------------|------|-------------------|
| `→` | `->` | TRANSFER | Pass information, memory slice, or control token to target |
| `?` | `?` | QUERY | Request information from target |
| `!` | `!` | ASSERT | Affirm a fact with optional confidence |
| `~` | `~` | APPROXIMATE | Probabilistic statement; always paired with `conf:` |
| `∑` | `SUM` | AGGREGATE | Consolidate multiple upstream inputs |
| `∂` | `DELTA` | DELTA | Report a measurable state change; always paired with `delta:` |
| `⊕` | `MERGE` | MERGE | Fuse two divergent contexts into one |
| `⊗` | `CONFLICT` | CONFLICT | Report an unresolved contradiction between sources |
| `↑` | `^` | ESCALATE | Escalate to a human or higher-authority Aeon |
| `↓` | `v` | DELEGATE | Delegate a subtask to a sub-Aeon or tool |
| `✓` | `OK` | CONFIRM | Validate, approve, or acknowledge |
| `✗` | `NO` | REJECT | Reject, block, or deny |

### ASCII aliases

When Unicode glyphs cannot be rendered (legacy terminals, log files), ASCII aliases
are valid in input. The canonical form always uses Unicode glyphs.

---

## 4. Canonical Form and Hashing

The **canonical form** is used for Civic Ledger hashing and equality comparison:

1. Normalize `AEON_ID` and `TARGET` to uppercase.
2. Replace ASCII verb aliases with Unicode glyphs.
3. Sort modifiers alphabetically by key.
4. Strip all leading/trailing whitespace.

```python
# Example
canonical = "ARIA_01 → NEXUS_CORE [civic:sha256:a3f...] [conf:0.92] [context:user_health]"
civic_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

The SHA-256 of the canonical form is the **Z-L Civic Hash** for that message.

---

## 5. Examples

### 5.1 Memory transfer between Aeons

```z-l
ORACLE_03 → ARIA_01 [context:episodic:last_3_sessions] [conf:0.87]
```

> "Oracle transfers episodic memory (last 3 sessions) to Aria with 87% confidence."

### 5.2 Threat assertion from Sentinel

```z-l
GUARDIAN_07 ! threat:prompt_injection [delta:+1] [civic:sha256:a3f4b2c1...]
```

> "Guardian asserts a prompt injection detection, +1 incident count, linked to prior audit entry."

### 5.3 Escalation to human

```z-l
ARIA_01 ↑ USER:JOHN [context:ambiguous_command] [conf:0.41]
```

> "Aria escalates to user John — command intent unclear, confidence only 41%."

### 5.4 Delegation to sub-Aeon

```z-l
NEXUS_CORE ↓ ANALYST_02 [context:kpi_report:Q2] [ttl:3600]
```

> "Nexus delegates the Q2 KPI report task to Analyst, valid for 1 hour."

### 5.5 Conflict report

```z-l
ORACLE_03 ⊗ NEXUS_CORE [context:user_preference:model_choice] [payload:ollama_vs_gemini]
```

> "Oracle reports a contradiction between its knowledge and Nexus's about the user's preferred model."

### 5.6 WisdomRule encoding

Z-L provides a compact encoding for WisdomRules that travel over Z-Sync:

```z-l
ARIA_01 ! wisdom:rule:prefer_structured_output [conf:0.95] [delta:+1] [civic:sha256:e7d...]
```

> "Aria asserts a new WisdomRule: prefer structured output. Confidence 95%, absorbed once."

### 5.7 Chained thread (tamper-evident)

```z-l
# Message 1
GUARDIAN_07 ! threat:pii_detected [delta:+1]
# civic hash of message 1: abc123...

# Message 2 — chains to message 1
ARIA_01 ↑ USER:JOHN [context:pii_in_response] [civic:sha256:abc123...]
```

---

## 6. Transport over Z-Sync

Z-L messages travel as line-delimited JSON over Z-Sync HTTPS push/pull:

```json
{
  "zl_version": "0.1",
  "message": "ORACLE_03 → ARIA_01 [context:episodic:last_3_sessions] [conf:0.87]",
  "civic_hash": "e3b0c44298fc1c149afb...",
  "timestamp": "2026-05-22T18:00:00Z",
  "aeon_id": "ORACLE_03"
}
```

The `message` field contains the canonical Z-L string. The `civic_hash` is independently
verifiable by the receiver. Tampered messages are rejected by the parser.

---

## 7. Security Properties

| Property | Mechanism |
|----------|-----------|
| Integrity | SHA-256 civic hash on canonical form; tampered messages rejected on parse |
| Non-repudiation | Civic Ledger records every Z-L message with hash chain |
| Replay protection | `ttl:` modifier + timestamp in transport envelope |
| Scope limitation | `TARGET` is explicit; no broadcast without explicit `*` target (reserved) |

---

## 8. Implementation Notes

- **Parser:** `cli/zana/core/zl_parser.py` — `ZLMessage` dataclass, `parse()`, `encode()`, `civic_hash()`
- **Civic Ledger integration:** every `parse()` call with `record=True` writes to `SentinelLiteDB`
- **Z-Sync integration:** `cli/zana/commands/sync.py` — messages serialized as line-delimited JSON
- **WisdomRule encoding:** `cli/zana/core/wisdom.py` — `WisdomRule.to_zl()` / `WisdomRule.from_zl()`

---

## 9. Versioning

This is Z-L v0.1 (parser + spec). Breaking changes to the grammar will increment the
major version. New modifiers are backwards-compatible (minor version bump).

---

*Z-L is part of the open Z-Protocol stack. MIT License.*
