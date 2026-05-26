<div align="center">

<img src="assets/zana_logo.svg" width="160" alt="ZANA — Zero Autonomous Neural Architecture"/>

# ZANA Core

**Every person in the world can have their own Aeon.**

*Your memories. Your evolution. Your rules. Running on your hardware.*

---

[![Version](https://img.shields.io/badge/ZANA-v3.15.0-10b981?style=for-the-badge)](https://github.com/Kemquiros/zana-core)
[![License](https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge)](LICENSE)
[![Engine](https://img.shields.io/badge/Engine-Python_+_Rust-e879f9?style=for-the-badge)](https://github.com/Kemquiros/zana-core)
[![ZFI](https://img.shields.io/badge/ZFI_Score-100%2F100-22c55e?style=for-the-badge)](#zfi--zana-fitness-index)
[![Paper](https://img.shields.io/badge/📄_Paper-arXiv-7c3aed?style=for-the-badge)](docs/paper/zana_paper.pdf)
[![Platform](https://img.shields.io/badge/Linux_·_macOS_·_Windows-6d28d9?style=for-the-badge)](#quick-start)

</div>

---

## What is ZANA?

The current AI paradigm concentrates intelligence in a handful of corporations that accumulate unlimited data about every user, control the models that "think for you," and define what you remember, how you evolve, who you are digitally.

ZANA inverts this with a single architectural principle:

```
┌─────────────────────────────────────────────────┐
│  YOUR AEON  (lives on your hardware)            │
│  Memory (4 stores) · Identity · Mastery Map     │
│  Civic Ledger · DNA · WisdomRules               │
└──────────────────────┬──────────────────────────┘
                       │  Z-Protocol (open, free)
                       ↓
┌─────────────────────────────────────────────────┐
│  PROCESSING  (interchangeable — your choice)    │
│  Ollama · Claude · Gemini · GPT-4o · Mistral    │
│  Groq · DeepSeek · LLaMA · Gemma · any model   │
└─────────────────────────────────────────────────┘
```

**Your Aeon is your digital soul. The model is the compute engine.
No one should own your soul.**

---

## Quick Start

> **No Docker required to start.** ZANA runs offline on any machine with Python 3.12+.
> Docker unlocks the full stack (ChromaDB, PostgreSQL, voice). Start without it.

### Linux / macOS
```bash
curl -LsSf https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.sh | sh
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.ps1 | iex
```

### Manual (pip / pipx)
```bash
pip install pipx
pipx install vecanova-zana
zana init        # 4 questions, then you're done
zana chat        # start talking — no Docker, no accounts, no API key required
```

### Standalone binary (no Python needed)
Download the binary for your platform from [GitHub Releases](https://github.com/Kemquiros/zana-core/releases/latest):
- `zana-linux-x86_64`
- `zana-windows-x86_64.exe`
- `zana-macos-arm64`

Then run `zana init` → `zana chat`.

### Full stack (optional — power users)
```bash
zana start       # launches Docker services: ChromaDB, PostgreSQL, Neo4j, ARIA UI
zana status      # check all services
zana stop        # shut everything down
```

> **Guides:** [Linux](docs/INSTALL_LINUX.md) · [macOS](docs/INSTALL_MACOS.md) · [Windows](docs/INSTALL_WSL.md) · [User Manual](docs/USER_MANUAL.md)

---

## Your Aeon

An Aeon is not a chatbot. It is a sovereign cognitive entity that:

- **Remembers** — every conversation, document, and decision you've ever had with it
- **Reasons** — step by step, symbolically, not just word by word
- **Evolves** — its skills improve the more you use it, while you sleep
- **Protects** — your data never leaves your hardware unless you explicitly choose it
- **Learns collectively** — shares improvements with other Aeons without sharing your data

| What your Aeon does | What it means for you |
|---|---|
| 🧠 **Persistent Memory** | Every idea, note, and conversation — indexed and searchable in under 50ms |
| ⚙️ **Code Agent** | Describe what you want. ZANA plans, writes, and tests while you do something else |
| 📊 **Business Intelligence** | Ask questions across your contracts, KPIs, and reports — connected |
| 🔬 **Research** | Drop papers or links. ZANA maps connections and surfaces what matters |
| 🛡️ **Private by design** | No telemetry. No accounts. No data sent anywhere without your permission |
| 🌱 **Self-improving** | Skills evolve automatically. The Aeon sharpens every day |
| 🎓 **Adaptive tutor** | Remembers what confused you and adjusts how it explains things |
| 🌐 **Model-agnostic** | Swap your LLM with one environment variable — the Aeon stays |

---

## Aeon Evolution — Mastery Map

Your Aeon grows as you grow. Every interaction advances its understanding of your path.

```
Seed          First interaction — the Aeon awakens
  ↓
Larva         Patterns emerge — basic skills learned
  ↓
Warrior       Tactical autonomy — proactive assistance  ← current default
  ↓
Champion      Real proactivity — anticipates before you ask
  ↓
Legend        Mastery — contributes skills to the global Agora
  ↓
Singularity   Full user-Aeon cognitive fusion
```

The rank reflects genuine accumulated wisdom — not a progress bar.

---

## Architecture — Five Pillars

| Pillar | Module | What it does |
|---|---|---|
| ⚔️ **Sentinel** | `armor/` (Rust) | Blocks PII and prompt injection at **2.1 µs/request** |
| 📚 **Archivist** | `episodic/`, `rust_core/`, `world_model/`, `procedural_memory/` | Four memory stores: Semantic (ChromaDB), Episodic (PostgreSQL + pgvector), World Model (Neo4j), Procedural Skills (JSON + Q-Learning) |
| 📊 **Analyst** | `reasoning_engine/` (Rust), `swarm/` | Exact Math Logic (EML) — symbolic reasoning that never hallucinates numbers |
| ⚙️ **Operator** | `orchestrator/graph.py`, `mcp/` | LangGraph pipeline: Orchestrator → Planner → Executor → Critic → Compressor → Chronicler |
| 📣 **Herald** | `sensory/` (FastAPI), `aria-ui/` (Next.js), `telegram_bot/` | Voice, vision, text, WebSocket — multilingual |

### The Steel Core (Rust)

Three compiled `.so` binaries handle performance-critical work:

| Binary | What it does | Latency |
|---|---|---|
| `zana_steel_core.so` | Kalman filter, Policy Brain (RL), EML operator | 1.4–18 µs |
| `zana_armor.so` | PII detection + prompt injection guard | 2.1 µs |
| `zana_audio_dsp.so` | Voice activity detection, Whisper preprocessing | real-time |

All three compile automatically on first `zana start`. Rust installs itself if missing.

### Infrastructure

| Service | Port | Role |
|---|---|---|
| Sensory Gateway (FastAPI) | 54446 | Main API entry |
| ARIA UI (PWA) | 54448 | Web interface |
| PostgreSQL + pgvector | 55433 | Episodic memory |
| Redis | 56380 | Session cache |
| Neo4j | 57474 | World model graph |
| Caddy | 80 / 443 | Reverse proxy + TLS |

---

## The Z-Protocol Stack

Open protocols — free to implement, extend, and fork:

| Protocol | Purpose | Status |
|---|---|---|
| **Z-Sovereign** | Sentinel + Civic Ledger — what your Aeon protects | ✅ Live |
| **Z-Identity** | DNA + Mastery Map — who your Aeon is | ✅ Live |
| **Z-Memory** | 4-store memory architecture | ✅ Live |
| **Z-Think** | Orchestrator + Symbolic Reasoning (EML) | ✅ Live |
| **Z-Express** | Herald — multimodal, multilingual | ✅ Live |
| **Z-Civic** | Immutable SHA-256 reasoning audit | ✅ Live |
| **Z-Skill** | Open skill format (agentskills.io compatible + extensions) | 🔄 v3.0 |
| **Z-Sync** | Privacy-preserving WisdomRule federation | 🔄 v3.5 |
| **Z-DNA** | Portable Aeon serialization (`.zaeon.enc`) | 🔄 v3.5 |
| `zaeon://` | Universal Aeon identity URI | 🔄 v3.5 |

---

## Model Providers

ZANA is model-agnostic. Swap your LLM with one environment variable:

| Provider | Activation |
|---|---|
| Anthropic Claude | `ANTHROPIC_API_KEY=sk-...` |
| OpenAI GPT | `OPENAI_API_KEY=sk-...` |
| Google Gemini | `GOOGLE_API_KEY=AIza...` |
| Groq | `GROQ_API_KEY=gsk_...` |
| Ollama (local, no key) | `OLLAMA_BASE_URL=http://localhost:11434` |
| Gemma 4 (recommended local) | `ZANA_PRIMARY_MODEL=ollama/gemma4` |

Each cognitive module (Curator, Compressor, Orchestrator) can use a different provider independently.

---

## CLI Reference

| Command | What it does |
|---|---|
| `zana start` | Boot the full ZANA stack |
| `zana stop` | Shut everything down |
| `zana status` | Running services and health |
| `zana setup` | Configure API keys or set up local Ollama |
| `zana chat` | Terminal conversation |
| `zana hardware` | Scan hardware and get model recommendations |
| `zana hardware --recommend` | Best models for your exact machine |
| `zana upgrade` | Update to the latest version |
| `zana embed <file>` | Index a document into memory |
| `zana aeon list` | Available Aeon agents |
| `zana aeon use <name>` | Switch active Aeon |

---

## ZFI — ZANA Fitness Index

ZANA scores itself across 7 cognitive pillars on every boot:

| Mode | Score |
|---|---|
| Cold (no Docker) | 89.8 / 100 |
| Hot (full stack) | 100.0 / 100 |

---

## What's New — v3.15.0 "Community Genesis"

- **The Agora v1.0** — sovereign skill marketplace. `zana skill publish --agora`, `zana skill search --agora`, `zana skill adopt`. GitHub-hosted JSON registry, no custom server, graceful offline fallback.
- **ZANA ID v1.0** — portable Aeon identity. `zana id export` → `.zaeon.enc` (AES-256-GCM + PBKDF2-SHA256, 390K iterations). `zana id import` on any machine. `zana id fingerprint` shows your 8-char Aeon ID.
- **NLU v2** — ZSM engine with 15 intents, pre-NLU keyword priority routing, zero API calls for intent classification.
- **Provider CLI** — `zana provider list/use`. Gemini 2.5, Claude 4.x, o3, Llama 3.3, OpenRouter (200+ models).
- **Quality Shield** — 1067 tests (0 failures). Ruff clean. Rust Sentinel layer.

See the full [CHANGELOG](CHANGELOG.md) for all previous releases.

---

## The Agora — Skill Marketplace

Skills are reusable AI workflows stored in `~/.zana/skills/<name>/`. The Agora is the P2P registry:

```bash
# Publish your skill to the community
zana skill publish --agora my-research-skill

# Discover skills from other Aeons
zana skill search --agora "code review"

# Adopt a skill locally
zana skill adopt code-reviewer-v2

# Your identity, portable and encrypted
zana id export              # → ~/.zana/aeon_backup.zaeon.enc
zana id import backup.zaeon.enc   # restore on any machine
zana id fingerprint         # → a3f7b21c
```

Skills are sovereign assets. They live on your machine. The registry is open. No intermediary owns your knowledge.

---

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full roadmap.

**v3.15.0 "Community Genesis" — Live ✅**

The Agora skill marketplace + ZANA ID portable identity. ZANA scales from personal tool to community ecosystem.

**Next — community-driven**

- Z-Sync — privacy-preserving WisdomRule federation
- `zaeon://` — universal Aeon identity URI
- WhatsApp + Discord Herald channels
- Issues and PRs welcome: https://github.com/Kemquiros/zana-core

---

## Technical Paper

[**ZANA: A Neuro-Symbolic Personal Cognitive AI Runtime (PDF)**](docs/paper/zana_paper.pdf)

---

## Contribute

ZANA is MIT licensed. The Z-Protocol is open.

```bash
git clone https://github.com/Kemquiros/zana-core
cd zana-core/cli
pip install -e ".[dev]"   # no Docker required for development
pytest cli/tests/ -q      # 176 tests
```

Ways to contribute:
- **Skills** — create a `SKILL.md` and open a PR to The Agora
- **Adapters** — new Herald channels (Telegram already done, WhatsApp, Discord, Signal welcome)
- **Languages** — translate `zana init` onboarding wizard
- **Providers** — new model adapters (LiteLLM-compatible)
- **Armor** — Rust security audits and contributions
- **Docs** — user guides, tutorials, video walkthroughs

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Issues labeled [`good first issue`](https://github.com/Kemquiros/zana-core/issues?q=label%3A%22good+first+issue%22) are the best place to start.

---

## Acknowledgements

With gratitude to: `eglejsr`, `ferchus_nandus`, `domination`, `kamo`, `virtus_sapiens`, `oma_fren`, `xanderx_monkey`.

---

<div align="center">

[![Ko-fi](https://img.shields.io/badge/Support_ZANA-Ko--fi-red?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/kemquiros)

Built with honor in Medellín, Colombia. 🇨🇴
**[VECANOVA](https://vecanova.com)** · MIT License

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*

</div>
