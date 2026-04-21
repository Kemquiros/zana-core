# ZANA Public Roadmap

> The stable cognitive layer in a world where AI changes every six weeks.

ZANA is a **plug&play architecture**: swap your LLM provider with one env var.
Claude → GPT-4o → Gemini → Llama 3 (Ollama) → Groq — ZANA doesn't care.
The cognitive runtime, memory, and reasoning stay constant.

Status markers: **shipped** · **in progress** · **next** · **future**

---

## v2.0 — Foundation (shipped)

The sovereign AI runtime.

- **Neuro-symbolic core** — LLM + CLIPS-pattern Rust reasoning engine
- **LiteLLM router** — Claude / GPT / Gemini / Groq / **Ollama (local)** behind one env var
- **4-store memory** — semantic (ChromaDB) · episodic (PostgreSQL+pgvector) · world model (Neo4j) · procedural (JSON)
- **Armor layer** — PII + prompt-injection guard in Rust at 2.1 µs
- **Kalman context window** — latent state vector, not raw token dump
- **ZFI (ZANA Fitness Index)** — cognitive health score across 7 pillars
- **CLI `zana`** — `start · stop · status · chat · login · embed · upgrade`
- **Aeon Fleet** — 8 specialized agents: Sentinel · Archivist · Analyst · Operator · Herald · Forge · Scholar · Watcher
- **`zana aeon`** — `list · use · recommend · status`
- **PWA (aria-ui)** — mobile/web interface, 6 locales, installable
- **Desktop (Tauri v2)** — Linux (.deb · .AppImage) · macOS (.dmg) · Windows (.msi)
- **Curl installer** — one line, works on Linux / macOS / WSL2

---

## v2.1 — Power Users (shipped)

Full observability and manual cognitive control.

- **`zana doctor`** — complete system audit: runtime, services, env, Aeon state (like `mise doctor`)
- **`zana memory search <query>`** — semantic search directly into ChromaDB vault
- **`zana memory recall [n]`** — last N episodic memories from PostgreSQL
- **`zana memory stats`** — collection sizes across all 4 stores
- **`zana reason <fact>`** — manual forward-chaining in the Rust engine; displays deduction trace
- **`zana reason --remote`** — escalates to swarm if local rules don't cover the fact
- **`zana shadow enable/disable/status`** — Shadow Observer daemon: silent background monitoring for meta-evolution
- **Ollama** listed in `zana doctor` as optional local LLM service (port 11434)

---

## v2.2 — Swarm Layer (shipped)

Coordinated multi-Aeon evolutionary fleet.

- **`zana swarm init [--warriors N] [--generations N]`** — bootstrap Red Queen
- **`zana swarm status [--watch]`** — live warrior dashboard: ID, stage (Larva→Warrior→Legend), generation, fitness, DNA hash
- **`zana swarm stop`** — graceful shutdown of the fleet
- **`zana swarm sync`** — pull community-validated WisdomRules from the Wisdom Hub (LLMGuard validated)
- **`zana swarm query <fact_key>`** — manual distributed remote query: ask peers for rules covering a fact
- Aeon evolution tiers: **Larva → Warrior → Legend** (driven by fitness + absorbed rules)
- DNA fingerprinting (SHA-256) for architecture sharing via A2A protocol

---

## v2.3 — Messaging Interfaces (next)

ZANA everywhere — no app install required for end users.

- **Telegram bot** — `zana telegram connect` wires your ZANA instance to a Telegram bot token
  - Commands: `/sense <text>` · `/recall <n>` · `/reason <fact>` · `/status` · `/aeon`
  - Streaming responses via Telegram message edits
  - Voice message → Whisper transcription → ZANA response → TTS reply
- **WhatsApp** — Meta Cloud API integration (requires Business account)
  - Same command surface as Telegram via natural language parsing
  - Media: images and voice notes pass through the multimodal pipeline
- Webhook manager: `zana-gateway` handles inbound hooks from both platforms
- Privacy: messages pass through Armor layer before hitting the LLM

---

## v3.0 — Sovereign Identity (future)

ZANA as a persistent, portable digital identity layer.

- **ZANA ID** — cryptographically signed cognitive profile; moves across devices
- **OAuth device flow** — browser-free auth for headless environments
- **Private cloud sync** — E2E-encrypted memory sync; no vendor lock-in
- **Civic Ledger** — public audit trail of reasoning decisions, SHA-256 signed
- **Public rule governance** — every RuleBase change signed and visible in the PWA

---

## v3.x — Open Platform (future)

ZANA as an ecosystem substrate.

- **MCP servers** — `zana-memory · zana-episodic · zana-world · zana-symbiosis` in the MCP registry
- **ZANA SDK** — embed the runtime in any Python or Rust project in 3 lines
- **Plugin API** — third-party Aeons installable via `zana aeon install <id>`
- **KoruOS integration** — ZANA as the AI substrate of KoruOS (symbiosis bridge built)
- **Multi-provider Aeon routing** — each Aeon can pin its own LLM: Forge → Opus, Watcher → Ollama local

---

## Plug&Play Provider Matrix

| Provider        | How to activate                              |
|-----------------|----------------------------------------------|
| Anthropic Claude| `ANTHROPIC_API_KEY=sk-...`                   |
| OpenAI GPT      | `OPENAI_API_KEY=sk-...`                      |
| Google Gemini   | `GOOGLE_API_KEY=AIza...`                     |
| Groq            | `GROQ_API_KEY=gsk_...`                       |
| Ollama (local)  | `OLLAMA_BASE_URL=http://localhost:11434`      |
| Any LiteLLM     | `ZANA_MODEL=provider/model-name`             |

No code changes. One env var. ZANA adapts.

---

## What we are not building

- A chat wrapper around a single LLM
- A hosted service with vendor data retention
- A replacement for your LLM provider — ZANA routes to whichever you choose

---

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*
