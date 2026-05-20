# Show HN Post — Hacker News

**Timing:** Tuesday–Thursday, 7–9 AM EST (HN peaks early morning US East)
**Character limit:** Title ≤ 80 chars
**Tone:** Technical, honest, no hype

---

## Title

```
Show HN: ZANA – A sovereign personal AI runtime (Python+Rust, MIT, offline-first)
```

*(80 chars exactly)*

Alternative:
```
Show HN: ZANA – local AI with persistent memory, Rust PII guard, SHA-256 audit log
```

---

## Body (submitted as the first comment — HN convention for Show HN)

---

ZANA (Zero Autonomous Neural Architecture) is a personal AI runtime I've been building for 2 months (the idea has been brewing since 2025), now open-sourced under MIT.

**The core architectural idea:** separate "soul" from "compute." Your Aeon (memory, identity, evolution, reasoning audit) lives on your hardware. The LLM is interchangeable — swap providers with one environment variable without touching the Aeon.

```bash
pip install vecanova-zana
zana init    # 4 questions
zana chat    # running, no Docker, no cloud
```

**What's technically interesting:**

*Rust armor layer* — PII detection + prompt injection guard implemented in Rust (`zana_armor.so`). Measures at 2.1µs per request in benchmarks. Compiles automatically on first `zana start`.

*EML (Exact Math Logic)* — a symbolic arithmetic engine in Rust that routes math operations away from the LLM entirely. Results are provable (deterministic), not probable. Prevents hallucination on numeric tasks structurally.

*4-store memory architecture* — Semantic (ChromaDB), Episodic (PostgreSQL + pgvector), World Model (Neo4j), Procedural (JSON + Q-Learning). For SPROUT tier (no Docker), all four degrade gracefully to SQLite FTS5.

*Civic Ledger* — every reasoning decision is SHA-256 logged and queryable. `zana sentinel ledger` shows the immutable audit trail. The idea: if an AI makes a decision that affects you, you should be able to audit exactly why.

*ZSM (ZANA Sovereign Machine)* — 15 offline intents that run without any LLM at all (math, reminders, vault, time, economy basics, language lookup, etc.). The SPROUT tier is genuinely useful air-gapped.

*WisdomRules auto-mining* — a background scheduler mines past sessions into skill proposals every 24h. The user reviews and approves them. Accumulated approved skills raise the Aeon's "Mastery Map" rank.

**Stack:**
- CLI: Python 3.12, Typer, Rich
- Security + reasoning: Rust (stable)
- Memory: SQLite FTS5 (offline) → ChromaDB + PostgreSQL (full stack)
- Orchestration: LangGraph
- Inference: LiteLLM router (Ollama, Anthropic, OpenAI, Groq, Gemini, anything)
- CI: GitHub Actions, ruff, mypy, pytest (580 tests), cargo clippy

**What's missing / honest caveats:**
- Mobile app: not yet
- True P2P federation (Z-Sync v1.0 is pull/push over HTTPS — the gossip-protocol design exists but is not yet implemented)
- Windows without WSL: install.ps1 exists, less battle-tested than Linux/macOS
- The "full stack" Docker setup is complex — the SPROUT tier is the battle-tested path

**Paper:** [ZANA: A Neuro-Symbolic Personal Cognitive AI Runtime](docs/paper/zana_paper.pdf) — documents the architecture formally.

GitHub: https://github.com/Kemquiros/zana-core

---

**[Posting notes for HN]:**
- HN users will read the code. Make sure the GitHub repo is clean before posting.
- First comment should be the technical details above — post it immediately after submitting.
- Expected pushback: "just use Ollama + Open WebUI" → answer: those don't have persistent memory across sessions, PII guard at request time, or the Civic Ledger audit trail.
- Expected question: "why Rust for the armor layer and not Python?" → answer: 2.1µs vs ~50µs in Python at the same logic. For every user message, every tool call, the armor runs. Latency compounds.
- Do NOT over-claim. Say clearly what's not done yet.
