<div align="center">

<img src="assets/zana_logo.svg" width="180" alt="ZANA — Zero Autonomous Neural Architecture"/>

# ZANA Core

**Your AI. Your hardware. Your rules.**

*The sovereign cognitive layer that remembers, reasons, and evolves — without the cloud.*

---

[![Version](https://img.shields.io/badge/ZANA-2.9.12-7c3aed?style=for-the-badge)](https://github.com/Kemquiros/zana-core)
[![License](https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge)](LICENSE)
[![Engine](https://img.shields.io/badge/Engine-Python_+_Rust-e879f9?style=for-the-badge)](https://github.com/Kemquiros/zana-core)
[![ZFI Score](https://img.shields.io/badge/ZFI_Score-100%2F100-22c55e?style=for-the-badge)](https://github.com/Kemquiros/zana-core)
[![Paper](https://img.shields.io/badge/📄_Paper-PDF-7c3aed?style=for-the-badge)](docs/paper/zana_paper.pdf)
[![Platform](https://img.shields.io/badge/Platform-Linux_·_macOS_·_Windows_WSL-6d28d9?style=for-the-badge)](#quick-start)

</div>

---

## What is ZANA?

ZANA is a personal AI that lives entirely on your hardware. It remembers every conversation, document, and decision you've ever had with it. It reasons step by step, not just word by word. It gets sharper the more you use it. And it never shares your data with anyone.

You install it once. It runs locally via Docker. You talk to it through a web browser, the command line, or Telegram. No subscription. No cloud. No vendor lock-in. Swap the underlying AI model with a single environment variable.

---

## Quick Start

**Linux / macOS**
```bash
bash <(curl -LsSf https://zana.vecanova.com/install.sh)
```

**Windows (WSL 2)**
```powershell
# Step 1 — PowerShell (Admin): installs Ubuntu, restart when done
wsl --install
```
```bash
# Step 2 — Inside Ubuntu terminal
bash <(curl -LsSf https://zana.vecanova.com/install.sh)
```

After installation, run `zana start` and open **http://localhost** in your browser.

> **Platform guides:**
> - 🐧 [Linux Guide](docs/INSTALL_LINUX.md)
> - 🍎 [macOS Guide](docs/INSTALL_MACOS.md)
> - 🪟 [Windows / WSL 2 Guide](docs/INSTALL_WSL.md) ← *Full step-by-step*
> - 📖 [User Manual](docs/USER_MANUAL.md)

---

## What can ZANA do?

| Use Case | What it means for you |
|---|---|
| 🧠 **Personal Memory** | Never lose an idea again. Every document, note, and conversation — indexed and searchable in under 50ms |
| ⚙️ **Code Agent** | Describe what you want to build. ZANA plans, writes, and tests the code while you do something else |
| 📊 **Business Intelligence** | Ask questions about your data. ZANA connects the dots across contracts, KPIs, and reports |
| 🔬 **Research** | Drop in papers or links. ZANA maps connections, spots contradictions, and surfaces what matters |
| 📄 **Document Q&A** | Upload any file. Ask anything. Get answers with exact sources — across hundreds of documents |
| 🛡️ **Private by design** | Everything stays on your machine. No telemetry. No accounts. No data sent anywhere |
| 🌱 **Self-improving** | While you sleep, ZANA refines its own skills on your data. It gets sharper every day |
| 🎓 **Personal Tutor** | ZANA remembers what confused you last week and adjusts how it explains things today |

---

## CLI Reference

| Command | What it does |
|---|---|
| `zana start` | Boot the full ZANA stack (Docker + gateway + UI) |
| `zana stop` | Shut everything down |
| `zana status` | Show which services are running and their health |
| `zana setup` | Interactive wizard: configure API keys or set up local Ollama |
| `zana chat` | Start a conversation in the terminal |
| `zana hardware` | Scan your hardware and get LLM model recommendations |
| `zana hardware --recommend` | Show the best models for your exact machine |
| `zana hardware --install` | Install llmfit (hardware model recommender) |
| `zana upgrade` | Update to the latest version |
| `zana login` | Set or rotate your authentication token |
| `zana embed <file>` | Embed a document into ZANA's memory |
| `zana aeon list` | List all available Aeon agents |
| `zana aeon use <name>` | Switch to a specific Aeon |

---

## v2.9 — What's new

### Ollama / Local AI Support
No API key? No problem. `zana setup` now guides you through connecting to [Ollama](https://ollama.com) in three steps: verify connection → pick your model → live inference test. ZANA writes the config automatically. You never see a config file unless you want to.

### Hardware Intelligence (`zana hardware`)
ZANA uses [llmfit](https://github.com/AlexsJones/llmfit) to scan your RAM, GPU, and CPU, then recommends which language models will actually run well on your machine. The model picker in `zana setup` shows llmfit-recommended models first with a badge.

### Works on Windows via WSL 2
Full Windows compatibility. The installer detects WSL, sets up the Obsidian vault on the Windows-side path, and installs Rust + build tools automatically. See the [Windows Guide](docs/INSTALL_WSL.md).

### Self-healing Upgrade
`zana upgrade` no longer requires a published GitHub Release. It checks the latest commit on main and offers to update. One command — always current.

### Sovereign Inference (any provider)
Swap your LLM provider with one environment variable. Anthropic, OpenAI, Gemini, Groq, Ollama — ZANA doesn't care. Each cognitive module (curator, compressor, orchestrator) can use a different provider independently.

| Provider | How to activate |
|---|---|
| Anthropic Claude | `ANTHROPIC_API_KEY=sk-...` |
| OpenAI GPT | `OPENAI_API_KEY=sk-...` |
| Google Gemini | `GOOGLE_API_KEY=AIza...` |
| Groq | `GROQ_API_KEY=gsk_...` |
| Ollama (local) | `OLLAMA_BASE_URL=http://localhost:11434` |
| Gemma 4 | `ZANA_PRIMARY_MODEL=ollama/gemma4` |

### Context Compression
Long sessions no longer slow ZANA down. The orchestrator automatically summarizes conversation history before it grows too large — language-aware, with anti-thrashing protection.

### Trajectory Capture
Every completed session is saved to `data/trajectories/` in ZANA native and ShareGPT JSONL formats. This is the foundation for fine-tuning a sovereign ZANA model on real interaction data.

### Skill Lifecycle (Curator Pattern)
Procedural skills are automatically reviewed every 30 minutes. Degraded skills are improved via Claude Haiku; skills with no recovery path are archived. Curation reports go to your Obsidian vault.

---

## Architecture

ZANA has five pillars, each a separate subsystem:

| Pillar | Module | What it does |
|---|---|---|
| ⚔️ **Sentinel** | `armor/` (Rust) | Blocks PII and prompt injection at 2.1 µs per request |
| 📚 **Archivist** | `episodic/`, `rust_core/`, `world_model/`, `procedural_memory/` | Four memory stores: semantic vector, episodic (PostgreSQL), world model (Neo4j), procedural skills (JSON) |
| 📊 **Analyst** | `reasoning_engine/` (Rust), `swarm/` | Forward-chaining symbolic reasoning + distributed Aeon swarm |
| ⚙️ **Operator** | `orchestrator/graph.py`, `mcp/` | LangGraph pipeline: Orchestrator → Planner → Executor → Critic → Compressor → Chronicler |
| 📣 **Herald** | `sensory/` (FastAPI), `aria-ui/` (Next.js), `telegram_bot/` | Multimodal input: voice, vision, text, WebSocket stream |

### Infrastructure

| Service | Port | Role |
|---|---|---|
| Sensory Gateway | 54446 | Main API entry point |
| Aria UI (PWA) | 54448 | Web interface |
| PostgreSQL + pgvector | 55433 | Episodic memory |
| Redis | 56380 | Session cache |
| Neo4j | 57474 | World model graph |
| Caddy | 80 / 443 | Reverse proxy + TLS |

### The Steel Core (Rust)

Three compiled `.so` binaries handle performance-critical work:

- **`zana_steel_core.so`** — Cognitive Kalman filter (1.4 µs/call), PolicyBrain (RL, 8–10 µs), EML operator
- **`zana_armor.so`** — PII detection + injection guard (2.1 µs/call)
- **`zana_audio_dsp.so`** — Passive voice activity detection

All three are compiled automatically on first `zana start`. Rust is installed automatically if missing.

---

## ZFI — ZANA Fitness Index

ZANA scores itself across 7 cognitive pillars on every boot:

| Mode | Score |
|---|---|
| Cold (no Docker) | 89.8 / 100 |
| Hot (full stack) | 100.0 / 100 |

---

## Technical Paper

The mathematical foundations — EML completeness, Kalman-based context management, and the cognitive architecture — are documented in our preprint:

[**ZANA: A Neuro-Symbolic Personal Cognitive AI Runtime (PDF)**](docs/paper/zana_paper.pdf)

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
