# ZANA Public Roadmap

> The stable cognitive layer in a world where AI changes every six weeks.

This document tracks what ZANA is building and where it is headed.
Status markers: **shipped** · **in progress** · **next** · **future**

---

## Now — v2.0 (shipped)

Foundation of the sovereign AI runtime.

- **Neuro-symbolic core** — LLM reasoning anchored by a CLIPS-pattern Rust engine
- **4-store memory** — semantic (ChromaDB) · episodic (PostgreSQL+pgvector) · world model (Neo4j) · procedural (JSON)
- **Armor layer** — PII + prompt-injection guard in Rust at 2.1 µs
- **LiteLLM router** — Claude / GPT / Gemini / Groq behind one env var; no rewrite when providers change
- **Kalman context window** — latent state vector instead of raw token dump
- **ZFI (ZANA Fitness Index)** — real-time cognitive health score across 7 pillars
- **CLI `zana`** — `start · stop · status · chat · login · embed · upgrade`
- **Aeon Fleet** — 8 specialized agents (Sentinel, Archivist, Analyst, Operator, Herald, Forge, Scholar, Watcher)
- **`zana aeon`** — `list · use · recommend · status`
- **PWA (aria-ui)** — mobile/web interface, 6 locales, installable
- **Desktop app (Tauri v2)** — Linux (.deb · .AppImage) · macOS (.dmg) · Windows (.msi)
- **Curl installer** — `curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | sh`

---

## Next — v2.1 (in progress)

Power-user layer and observability.

- `zana doctor` — full system health table (patrón: `mise doctor`)
- `zana memory search <query>` — semantic query into ChromaDB from the terminal
- `zana reason <fact>` — manual forward-chaining trigger for the Rust engine
- Benchmark dashboard in PWA — live ZFI chart, latency per pillar
- Aeon auto-selection — ZANA recommends the right Aeon based on detected task context, no manual `zana aeon use`
- Streaming TTS in desktop — real-time voice response via `edge-tts`

---

## v2.2 — Swarm Layer (next)

Coordinated multi-Aeon execution.

- `zana swarm init` — bootstrap Red Queen: 50 warriors, 2 000 generations
- `zana swarm status` — live warrior dashboard in the terminal
- Distributed reasoning (`Remote_Query`) — if local rules don't cover a fact, the swarm is queried
- Wisdom Hub sync — pull community-validated rules from the ZANA Grid; cryptographic signature per rule
- Aeon evolution — Larva → Warrior → Legend progression tied to solved tasks and absorbed rules

---

## v3.0 — Sovereign Identity (future)

ZANA as a persistent digital identity layer.

- **ZANA ID** — portable, signed cognitive profile; moves with the user across devices
- **OAuth device flow** — browser-free authentication, works in headless environments
- **Private cloud sync** — end-to-end encrypted memory sync across devices; no vendor lock-in
- **Civic Ledger** — public audit trail of reasoning decisions; SHA-256 signed, immutable
- **Public rule governance** — every change to the RuleBase is signed and visible in the PWA

---

## v3.x — Ecosystem (future)

ZANA as an open platform.

- **MCP servers** — `zana-memory · zana-episodic · zana-world · zana-symbiosis` published to the MCP registry
- **ZANA SDK** — embed the cognitive runtime in any Python or Rust application in 3 lines
- **Plugin API** — third-party Aeons installable via `zana aeon install <id>`
- **KoruOS integration** — ZANA as the AI substrate of KoruOS (symbiosis bridge already built)
- **Telegram interface** — `/sense · /recall · /reason` from any Telegram client

---

## What we are not building

- A general-purpose chat wrapper
- A hosted AI service with vendor data retention
- A replacement for your LLM provider — ZANA routes to whichever you choose

---

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*
