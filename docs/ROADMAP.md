# ZANA Public Roadmap

> The stable cognitive layer in a world where AI changes every six weeks.

ZANA is a **plug&play architecture**: swap your LLM provider with one env var.
Claude → GPT-4o → Gemini → Llama 3 (Ollama) → **Gemma 4** — ZANA doesn't care.
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
- **Aeon Fleet** — 8 specialized agents with unique digital personalities (**Digimon-style evolution**)
- **`zana aeon`** — `list · use · recommend · status`
- **PWA (aria-ui)** — mobile/web interface, 6 locales, **fully responsive**
- **Desktop (Tauri v2)** — Linux (.deb · .AppImage) · macOS (.dmg) · Windows (.msi)
- **Curl installer** — Poliglota one-liner: `curl | bash`

---

## v2.5 — Public Sovereignty (shipped)

The Hito 8 milestone: distributed trust and identity.

- **Civic Ledger** — SHA-256 immutable audit trail of every reasoning decision
- **Mastery Map** — Aeon evolution tiers: **Larva → Warrior → Legend**
- **Z-Network (Red Z)** — Decentralized swarm for sharing WisdomRules without data leakage
- **LLM Guard** — Active defense against prompt-injection and banned effects in external rules
- **Gemma 4** — Set as the default recommended local model for sovereign reasoning
- **SEO Sovereign** — Managed `robots.txt` and `sitemap.xml` for discovery without extraction

---

## v2.6 — Modular Projects (shipped)

Context management for builders.

- **Módulo de Proyectos** — Integrated task and file management directly into `zana-core`
- **Context-per-Project** — Memory scopes isolated by active project
- **Aeon Soul** — Forged conversational identity and unique 3D manifestations

---

## v2.9 — The Sovereign Bridge (in progress)

Ubiquity, Identity, and Autonomous Lifecycle.

- **The Update Pulse** — Background check every 4h; zero-downtime hot-swap deployment
- **ZANA ID** — OIDC/OAuth2 authentication with multi-tenant data isolation
- **Remote Access** — Automated Cloudflare/Tailscale secure tunnels
- **Curator Pattern** ✅ — Autonomous skill lifecycle (active → stale → archived). Heartbeat reviews degraded procedural memory every 30 min via Claude Haiku; curation logs persist to the Obsidian vault.
- **Context Compression** ✅ — Smart auto-summarization in the Orchestrator LangGraph (language-aware, anti-thrashing, graceful fallback). New `compressor` node with 3-way routing from `critic`.
- **Trajectory Capture** ✅ — Every completed session saved to `data/trajectories/` in ZANA native + ShareGPT JSONL. Pipeline toward fine-tuning a sovereign ZANA model.

---

## v3.0 — Planetary Intelligence (future)

ZANA as an indispensable tool for humanity.

- **Individual Pods** — OS-level process isolation for multi-tenant sovereignty
- **Collaborative Swarms** — Encrypted P2P knowledge sharing between ZANA instances
- **Sovereign identity** — Portable, signed digital soul across any infrastructure


---

## Plug&Play Provider Matrix

| Provider        | How to activate                              |
|-----------------|----------------------------------------------|
| Anthropic Claude| `ANTHROPIC_API_KEY=sk-...`                   |
| OpenAI GPT      | `OPENAI_API_KEY=sk-...`                      |
| Google Gemini   | `GOOGLE_API_KEY=AIza...`                     |
| Groq            | `GROQ_API_KEY=gsk_...`                       |
| Ollama (local)  | `OLLAMA_BASE_URL=http://localhost:11434`      |
| **Gemma 4**     | `ZANA_PRIMARY_MODEL=ollama/gemma4`           |

No code changes. One env var. ZANA adapts.

---

## What we are not building

- A chat wrapper around a single LLM
- A hosted service with vendor data retention
- A replacement for your LLM provider — ZANA routes to whichever you choose

---

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*
