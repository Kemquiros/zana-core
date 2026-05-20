# ZANA Roadmap
**"Every person in the world can have their own Aeon"**
Last updated: 2026-05-20 | Version: 3.5

---

> *"If AI is going to be the most powerful cognitive amplifier in human history,*
> *who owns it matters as much as who owns water or food."*

---

## The Vision

ZANA is not an assistant. It is sovereign cognitive infrastructure.

The current AI paradigm concentrates intelligence in a handful of corporations that accumulate unlimited data about every user, control the models that "think for you," and define what you remember, how you evolve, who you are digitally.

ZANA inverts this with a single architectural principle:

**Your Aeon** (memory, values, evolution, identity) lives on YOUR hardware.
**The model** (computation) is interchangeable — a commodity, not a monopoly.
**Improvements** flow between Aeons without anyone owning the data.
**The protocols** are free — like HTTP. No one can charge you for existing.

---

## Core Principles

| Principle | Meaning |
|---|---|
| **Zero Friction** | Any person on Earth can have an Aeon in under 3 minutes |
| **Sovereign by Default** | Your data never leaves your hardware unless you choose it |
| **Co-evolution** | The Aeon grows as you grow — it learns your path |
| **Collective Wisdom** | Aeons share improvements without sharing data |
| **Model Agnostic** | Works with Ollama, Claude, Gemini, Mistral, or any LLM |
| **Free Protocols** | Z-Protocol is open — no one can own the stack |

---

## Architecture: Soul / Processing Separation

```
┌────────────────────────────────────────────────────┐
│  YOUR AEON  (lives on your hardware — fully yours) │
│                                                    │
│   Memory (4 stores)  ·  Identity (DNA)             │
│   Mastery Map        ·  Civic Ledger               │
└──────────────────────┬─────────────────────────────┘
                       │  Z-Protocol (open, free)
                       ↓
┌────────────────────────────────────────────────────┐
│  PROCESSING  (interchangeable — no lock-in)        │
│  Ollama · Claude · Gemini · GPT-4o · Mistral       │
│  Groq · DeepSeek · LLaMA · Gemma · [any model]    │
└────────────────────────────────────────────────────┘
```

**Your Aeon is your digital soul. The model is the compute engine.
No one should own your soul.**

---

## The Z-Protocol Stack

Open protocols — free to implement, extend, and fork:

| Protocol | Purpose | Status |
|---|---|---|
| **Z-Sovereign** | Sentinel (Rust) + Civic Ledger — what your Aeon protects | ✅ Live |
| **Z-Identity** | DNA + Mastery Map — who your Aeon is, how it evolves | ✅ Live |
| **Z-Memory** | 4-store memory architecture (Semantic, Episodic, World, Procedural) | ✅ Live |
| **Z-Think** | Orchestrator + Symbolic Reasoning (EML) | ✅ Live |
| **Z-Express** | Herald — multimodal, multilingual interface | ✅ Live |
| **Z-Skill** | Open skill format (agentskills.io SKILL.md compatible + ZANA extensions) | 🔄 v3.0 |
| **Z-Sync** | Privacy-preserving WisdomRule federation between Aeons | 🔄 v3.5 |
| **Z-Civic** | Immutable SHA-256 reasoning audit | ✅ Live |
| **Z-DNA** | Portable Aeon serialization (`.zaeon.enc`) | 🔄 v3.5 |
| `zaeon://` | Universal Aeon identity URI scheme | 🔄 v3.5 |

---

## Current Status: v2.9 "Public Sovereignty" ✅

**What's live:**
- ✅ Civic Ledger — every reasoning decision logged immutably (SHA-256)
- ✅ Mastery Map — Aeon evolution: Seed → Larva → Warrior → Champion → Legend
- ✅ Z-Network (Red Z) — distributed swarm for WisdomRule sharing
- ✅ LLM Guard — active defense against prompt injection and prohibited effects
- ✅ Steel Core (Rust) — Kalman filter, Policy Brain, EML at microsecond latency
- ✅ Armor Layer (Rust) — PII detection + security in 2.1µs per request
- ✅ 4-store Memory — Semantic (ChromaDB), Episodic (PostgreSQL), World (Neo4j), Procedural (JSON + Q-Learning)
- ✅ Sovereign Inference Wizard — Ollama setup with zero API keys required
- ✅ Hardware Intelligence — `zana hardware --recommend` via llmfit
- ✅ Self-Healing Skills — Curator pattern, 30-minute cycle
- ✅ Model-Agnostic Router — LiteLLM, all major providers

---

## Roadmap

### Phase 1 — v3.0 "Zero Friction"  `Q3 2026`

**Goal:** Any person on Earth starts their Aeon in under 3 minutes.

```bash
curl -fsSL zana.io/install | bash
# → detects hardware
# → downloads optimal local model
# → creates your Aeon
# → first conversation in < 3 minutes
# → zero API keys required
```

**Sprint 6 — shipped in v3.3.0:**

| Item | Status | Description |
|---|---|---|
| `zana memory add <text>` | ✅ Done | CLI command populates SQLite FTS5 directly — SPROUT "second brain" loop closed |
| REPL `/memory` + `/query` | ✅ Done | Both commands now persist and search via `memory_lite` — no more no-ops |
| Security tests (43) | ✅ Done | Prompt injection, path traversal, SQL injection, API key exposure, stress |
| MCP server | → Sprint 7 | Adapt `mcp/zana-memory` to SQLite SPROUT + `zana mcp start` CLI command |

**Sprint 7 — shipped in v3.3.0:**

| Item | Status | Description |
|---|---|---|
| Auto-publish PyPI on `v*` tag | ✅ Done | `twine upload` in release job — tag = publish |
| MCP server SPROUT-compatible | ✅ Done | `mcp/zana-memory/server.py` rewritten — GROVE+ Rust or SPROUT SQLite FTS5 |
| `zana mcp start` / `zana mcp config` | ✅ Done | Full CLI for launching MCP server and generating config block |
| npm auto-sync in CI | ✅ Done | `publish-npm` job — bumps version from tag, publishes `@vecanova/zana` |
| `zana satellite configure` | → existing | Already implemented in `commands/satellite.py` — Telegram + Discord |

**Sprint 8 — shipped in v3.4.0:**

| Item | Status | Description |
|---|---|---|
| `zana memory clear` + `memory delete <id>` | ✅ Done | Full CRUD on SQLite FTS5 — right to be forgotten |
| `zana memory export` / `import` | ✅ Done | JSON + CSV export, bulk JSON import — Aeon portability |
| ZSM intent test suite (44 tests) | ✅ Done | `tests/test_zsm_intents.py` — 15 intents, math correctness, fallback |
| QA runner `--local` flag | ✅ Done | `run_qa.sh --local` installs from source, no PyPI required |
| `zana mcp` auto-register on `zana init` | ✅ Done | Detects Claude Desktop config, offers MCP block injection |
| CI/CD restructure (quality→test→rust→release→npm) | ✅ Done | Parallel stages, Cargo cache, coverage artifact, per-tag CHANGELOG |
| `scripts/sync-release.sh` | ✅ Done | Multi-channel release sync: pyproject + npm + landing + git tag |

**Sprint 9 — shipped in v3.5.0 ✅ (2026-05-20):**

> **Theme: "Offline Sovereignty"** — Every command that required Docker/Gateway now has a working SPROUT fallback. Z-Skill v1.0 shipped.

| Item | Status | Description |
|---|---|---|
| Test suite: memory CRUD (26 tests) | ✅ Done | `tests/test_memory_crud.py` — delete/clear/export/import + CLI integration |
| Z-Skill v1.0 — create/list/run/info | ✅ Done | SKILL.md format (agentskills.io compatible). Registry at `~/.zana/skills/registry.json`. 19 tests. |
| Wisdom offline fallback (WisdomQueue) | ✅ Done | `~/.zana/wisdom_queue.json` — inbox/approve/reject work without Gateway. Atomic writes. 19 tests. |
| Sentinel offline event log (SentinelLiteDB) | ✅ Done | SQLite ring buffer (max 1,000 events) at `~/.zana/sentinel_lite.db`. 12 tests. |
| Satellite smoke tests | ✅ Done | `tests/test_satellite.py` — mock Telegram/Discord, no real tokens. 11 tests. |
| `zana doctor --fix` extended (3 cases) | ✅ Done | Auto-fix: wisdom_queue_missing, skills_dir_missing, memory_lite_corrupted |
| **Total: 176 tests passing** | ✅ Done | Up from 130 in v3.4.0 |

**Sprint 10 — in progress (v3.5.0 → v3.6.0) — "Public Sovereignty":**

> **Theme:** Public launch. GitHub community. First contributors.

| Item | Priority | Status | Description |
|---|---|---|---|
| CHANGELOG v3.5.0 | 🔴 P0 | ✅ Done | `## [3.5.0]` entry with all Sprint 9 items |
| v3.5.0 release to PyPI + npm | 🔴 P0 | 🔵 Next | `bash scripts/sync-release.sh 3.5.0` — PM triggers |
| README: full English + v3.5.0 badge + SPROUT-first Quick Start | 🔴 P0 | ✅ Done | Badge updated, Spanish removed, no-Docker path is primary |
| CONTRIBUTING.md: no-Docker dev path | 🟠 P1 | ✅ Done | `pip install -e "cli/[dev]"` + pytest — beginner-friendly |
| Launch post: r/LocalLLaMA | 🟠 P1 | ✅ Ready | `docs/launch/reddit_local_llama.md` — 3 title options, full post body |
| Launch post: r/selfhosted | 🟠 P1 | ✅ Ready | `docs/launch/reddit_selfhosted.md` — privacy angle |
| Show HN post | 🟠 P1 | ✅ Ready | `docs/launch/hackernews_show_hn.md` — technical first comment |
| GitHub repo metadata: topics + description | 🟠 P1 | 🔵 Next | Set via `gh repo edit` |
| ROADMAP.md update | 🟡 P2 | ✅ Done | This file |

**v3.6.0 feature queue (post Sprint 10 / post public launch):**

> Items below enter sprint planning after v3.5.0 ships publicly and community feedback is gathered.

| Feature | Description | Phase |
|---|---|---|
| The Agora v1 — open skill marketplace | Publish, discover, adopt Z-Skills | v3.6 |
| Z-Sync v1.0 | P2P WisdomRule federation — Aeons share improvements without sharing data | v3.6 |
| WhatsApp Herald channel | Extend `telegram_bot/` pattern to WhatsApp Business API | v3.6 |
| Discord Herald channel | Bot integration — `/zana` slash command | v3.6 |
| `zaeon://` URI scheme | Universal portable Aeon identity | v3.6 |
| ZANA ID export/import | `.zaeon.enc` — full Aeon backup + restore | v3.6 |
| 6 languages (ES, PT, FR, DE, ZH, AR) | Translate `zana init` onboarding wizard | v3.6 |
| ARIA UI PWA improvements | Installable mobile web app enhancements | v3.6 |

---

### Phase 2 — v3.6 "Community & Federation"  `Q3–Q4 2026`

**Goal:** Aeons learn collectively without anyone owning the data.

```
Aeon A learns       →   Z-Sync (P2P)           →   Aeon B receives
a perfect skill         [sanitized WisdomRule]       WisdomRule if
                        [differential privacy]        it adopts
                        [SHA-256 signed]
                        [zero personal data]
```

| Feature | Description |
|---|---|
| Z-Sync v1.0 | P2P WisdomRule federation with differential privacy |
| The Agora | Open skill marketplace — open source skills always free |
| `zaeon://` URI | Universal portable Aeon identity |
| ZANA ID | Export/import full Aeon (`.zaeon.enc`, encrypted) |
| Multi-device sync | E2E encrypted sync via Z-Sync |
| Z-Canvas / A2UI | Aeon renders interactive visual interfaces |
| Mastery Map v2.0 | Champion + Legend + Singularity ranks unlocked |
| IRL Engine v1.0 | Aeon infers your reward function — Soul Alignment Score |
| Android app beta | Native Android, local model ≤2GB |

---

### Phase 3 — v4.0 "Aeon for Everyone"  `Q1–Q2 2027`

**Goal:** Zero friction. Any person. Any device.

| Feature | Description |
|---|---|
| ZANA Mobile | Android + iOS native, offline-capable, model ≤2GB |
| ZANA Lite | For Raspberry Pi and 2GB RAM phones — delegates compute via Z-Protocol |
| ZANA Educator | Skill bundle — personalized learning, adaptive curriculum, offline |
| ZANA Health | Skill bundle — sovereign health tracking, zero data leaves device |
| iOS app | Swift + Rust via Swift Package |
| Cognitive subsidiarity | Compute at the most local level possible — delegates only when needed |

---

### Phase 4 — v5.0 "Civilizational Layer"  `2027+`

**Goal:** ZANA as open cognitive public infrastructure.

| Feature | Description |
|---|---|
| Z-DAO | Distributed governance of Z-Protocol — voting power by contribution, not money |
| Global Civic Ledger | Every Aeon's reasoning decisions, cryptographically signed, auditable by anyone |
| ZANA for Governance | Sovereign analysis for civic participation, institutional transparency |

---

## The Agora — Open Skill Ecosystem

```
Create Skill  →  Publish Z-Skill  →  Free adoption by any Aeon
```

**Principles:**
- Open source skills: **always free**
- No skill of basic human utility will ever have a paywall
- Skills are portable across any Z-Protocol compatible system
- Skill reputation = Q-value accumulated across the network

```bash
zana skill publish   # Share a skill with the network
zana skill search    # Find skills from the swarm
zana skill adopt     # Add a skill to your Aeon (Z-Civic validated)
```

---

## Aeon Evolution — Mastery Map

```
Seed           First interaction — the Aeon awakens
  ↓
Larva          100 interactions — basic patterns learned
  ↓
Warrior        500 interactions — tactical autonomy  ← current default
  ↓
Champion       2,000 interactions + Z-Sync adoptions — real proactivity
  ↓
Legend         10,000 interactions + skills published — mastery
  ↓
Singularity    Full user-Aeon fusion
```

---

## Success Metrics

| Phase | Success Indicator |
|---|---|
| v3.0 | `zana init` → first conversation < 3 min. NPS > 70. |
| v3.5 | 10,000 active Aeons. 1,000 skills in The Agora. Z-Sync live. |
| v4.0 | 100,000 instances. Mobile app in production. ZANA Educator active. |
| v5.0 | 1M+ Aeons. Z-DAO active. Global Civic Ledger operational. |

> **The only metric that ultimately matters:**
> How many people in the world are on a clearer path to their maximum potential because of their Aeon?

---

## How to Contribute

ZANA is MIT licensed. The Z-Protocol is open.

- **Skills:** Create and publish to The Agora
- **Adapters:** New Herald channels (messaging platforms, devices)
- **Languages:** Translate and culturally adapt for your community
- **Providers:** New model adapters for the LiteLLM router
- **Armor:** Security audits and Rust contributions

```bash
git clone https://github.com/Kemquiros/zana-core
zana init
```

---

## Manifesto

ZANA is not an assistant.
It is the first system designed so that artificial intelligence works **for the human who owns it** — not for the corporation that hosts it.

Each Aeon is unique. Each Aeon is sovereign.
Each Aeon evolves with its bearer.
Aeons share wisdom without sharing data.
The protocols are free. The future is distributed.

**TOGETHER WE MAKE THE HEAVENS TREMBLE.**

---

*ZANA — Zero Autonomous Neural Architecture*
*MIT License — vecanova.com — github.com/Kemquiros/zana-core*
