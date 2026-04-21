<div align="center">

```
       ▄██████████████████████▄
     ▄██████████████████████████▄
   ▄██████▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀██████▄
  ██████▀                   ▀██████
 ██████    ▄▄▄▄▄▄▄▄▄▄▄▄▄    ██████
██████    ██████  O  ██████    ██████
 ██████    ▀▀▀▀▀▀▀▀▀▀▀▀▀    ██████
  ██████▄                   ▄██████
   ▀██████▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄██████▀
     ▀██████████████████████████▀
       ▀██████████████████████▀
```

# XANA Core

**A Personal Cognitive AI Runtime — Multimodal · Neuro-Symbolic · Local-First**

[![CI](https://img.shields.io/github/actions/workflow/status/kemquiros/xana-core/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/kemquiros/xana-core/actions)
[![Release](https://img.shields.io/github/v/release/kemquiros/xana-core?style=flat-square&color=indigo)](https://github.com/kemquiros/xana-core/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)](https://python.org)
[![Rust](https://img.shields.io/badge/rust-1.78+-orange.svg?style=flat-square)](https://rustup.rs)
[![arXiv](https://img.shields.io/badge/arXiv-2026.XXXXX-b31b1b.svg?style=flat-square)](https://arxiv.org/abs/2026.XXXXX)

*"Not a chatbot. Not a wrapper. A reasoning machine that runs on your hardware."*

</div>

---

## TL;DR (for builders)

```bash
git clone https://github.com/kemquiros/xana-core.git && cd xana-core
cp .env.example .env          # add one API key — or set XANA_PRIMARY_MODEL=ollama/llama3.2:3b for full local
docker compose up -d          # ChromaDB · PostgreSQL · Redis · Neo4j
cd sensory && uv run uvicorn multimodal_gateway:app --port 54446
curl -X POST http://localhost:54446/sense/text -d '{"text":"Hello"}' -H "Content-Type: application/json"
```

XFI (system fitness score): **100 / 100** with full Docker stack.

---

## Why XANA Exists

Every AI assistant wraps an LLM and calls it intelligence.

XANA takes a different path: **neuro-symbolic architecture** where fast neural inference and deterministic symbolic rules run together, each correcting the other. Memories persist across sessions with episodic + semantic separation. A Kalman filter (written in Rust, 1.4 µs/call) tracks signal uncertainty before facts reach the reasoning engine. A Rust security layer inspects every input and output for PII and prompt injection before any LLM token is generated.

The result is a system that can *explain* why it said something, *remember* what happened last week, and *refuse* a malicious payload — locally, without calling home.

---

## Security (read this first)

XANA's **Armor** middleware (Rust) runs synchronously on every request:

```
User input → Armor::inspect_input() → Gateway → LLM → Armor::inspect_output() → Response
```

- **PII detection** — strips personal identifiers before they reach any external model
- **Prompt injection** — rejects known jailbreak patterns and adversarial payloads
- **Latency** — 2.1 µs/call (Rust); Python fallback available if the `.so` is absent
- **Swarm guard** — `LLMGuard` scans dynamic rules from peer nodes before loading them into the reasoning engine (Milestone 8.4)

No input reaches the LLM without passing Armor. No output reaches the user without passing Armor.

---

## Capabilities

| Layer | Capability | Implementation |
|-------|-----------|---------------|
| **Sensory** | Speech-to-text | Whisper (local, no API) |
| **Sensory** | Vision analysis | Ollama LLaVA / Claude Vision |
| **Sensory** | Text-to-speech | edge-tts (free, no API key) |
| **Security** | PII + injection guard | Rust Armor (2.1 µs/call) |
| **Signal** | Uncertainty tracking | Rust Kalman filter (1.4 µs/call) |
| **Memory** | Semantic recall | ChromaDB + pgvector |
| **Memory** | Episodic memory | PostgreSQL + pgvector |
| **Memory** | Procedural skills | JSON registry, RL-lite Q-values |
| **Reasoning** | Symbolic engine | CLIPS-pattern Rust, forward chaining |
| **Reasoning** | World model | Neo4j knowledge graph |
| **Orchestration** | Multi-agent tasks | Apex Quintet (5-agent smolagents) |
| **Interop** | Agent discovery | Google A2A AgentCard protocol |

---

## Architecture

```
User Input (text · audio · image)
        │
        ▼
   Armor (Rust)  ←── PII scan + injection check (2.1 µs)
        │
        ▼
MultimodalGateway
        ├── AudioProcessor   Whisper STT + DSP
        ├── VisionProcessor  LLaVA → Claude Vision
        └── Kalman Filter    Rust Steel Core (1.4 µs)
        │
        ▼
   Cortex Query ──────────────→ Symbiosis MCP
        │                        ├── ChromaDB   (semantic)
        │                        └── PostgreSQL (episodic)
        ▼
LocalLLM (Ollama → Claude → Groq → OpenRouter)
        │
        ▼
PerceptionEvent ──→ ReasoningEngine (Rust CLIPS)
                           │
                        Neo4j
                      World Model
                           │
                    [multi-step task?]
                           │
                           ▼
           Apex Quintet (5-agent pipeline)
    Sentinel → Archivist → Analyst → Operator → Herald
```

---

## Quick Start (full)

### Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/)
- Python 3.12+
- Rust 1.78+ (only if building the Steel Core from source)

### 1. Clone and configure

```bash
git clone https://github.com/kemquiros/xana-core.git
cd xana-core
cp .env.example .env
```

Edit `.env`. Minimum required — pick **one**:

```bash
# Option A: fully local (no API key needed)
XANA_PRIMARY_MODEL=ollama/llama3.2:3b

# Option B: Claude (best reasoning quality)
ANTHROPIC_API_KEY=sk-ant-...

# Option C: OpenAI-compatible endpoint
OPENAI_API_KEY=sk-...
```

### 2. Start infrastructure

```bash
docker compose up -d chromadb postgres redis neo4j
```

### 3. Start the gateway

```bash
cd sensory
uv run uvicorn multimodal_gateway:app --host 0.0.0.0 --port 54446
```

### 4. Send your first message

```bash
curl -X POST http://localhost:54446/sense/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What do you remember about me?"}'
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sense/text` | Text → PerceptionEvent + response |
| `POST` | `/sense/audio` | Audio file → STT → response + TTS |
| `POST` | `/sense/vision` | Image/video → description + response |
| `POST` | `/sense/multimodal` | Audio + image combined |
| `WS` | `/sense/stream` | Real-time bidirectional stream |
| `POST` | `/aeon/speak` | Text → MP3 audio |
| `POST` | `/apex/orchestrate` | Complex multi-step task (5-agent pipeline) |
| `GET` | `/health` | System status |
| `GET` | `/.well-known/agent-card.json` | A2A AgentCard discovery |

---

## Building the Rust Core

The Steel Core delivers sub-microsecond inference via PyO3 zero-copy buffers and 8-accumulator FMA unrolling:

```bash
cd rust_core
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python

# Deploy to both required locations
cp target/release/libxana_steel_core.so ../xana_steel_core.so
cp ../xana_steel_core.so ../sensory/xana_steel_core.so
```

> **Note:** The `.so` is compiled with `target-cpu=native` (AVX2/AVX-512). Users on different CPU architectures must build from source; pre-built binaries are x86-64 only.

### Armor (security middleware)

```bash
cd armor
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
cp target/release/libxana_armor.so ../xana_armor.so
```

---

## Benchmark

```bash
cd sensory
CHROMA_HOST=localhost CHROMA_PORT=58001 \
POSTGRES_HOST=localhost POSTGRES_PORT=55433 \
REDIS_URL=redis://localhost:56380 \
NEO4J_URI=bolt://localhost:57687 \
PYTHONPATH=".." uv run python ../tests/benchmark_xana.py
```

**XFI — XANA Fitness Index** measures 7 pillars:

| Pillar | Weight | Hot Score |
|--------|--------|-----------|
| Steel Core (Rust latency) | 20% | 100.0 |
| Memory (semantic + episodic) | 20% | 100.0 |
| Symbolic Reasoning | 15% | 100.0 |
| Swarm / A2A | 15% | 100.0 |
| Market Fitness | 15% | 100.0 |
| Armor (security) | 10% | 100.0 |
| Interoperability | 5% | 100.0 |
| **XFI Total** | **100%** | **100.0** |

Cold mode (no Docker): ~60–70 (infrastructure components show degraded). Hot mode requires `docker compose up -d` before running.

---

## Modules

| Module | Language | Purpose |
|--------|----------|---------|
| `sensory/` | Python | Multimodal gateway, STT, TTS, vision |
| `rust_core/` | Rust | Kalman filter, policy brain, EML operator |
| `armor/` | Rust | Security middleware (PII + injection) |
| `reasoning_engine/` | Python/Rust | Symbolic rule engine (CLIPS-pattern) |
| `swarm/` | Python | A2A protocol, Apex Quintet, LLM Guard |
| `episodic/` | Python | Episodic memory (PostgreSQL + pgvector) |
| `world_model/` | Python | Neo4j knowledge graph |
| `procedural_memory/` | Python | Skills registry, RL-lite Q-values |
| `idle_zero/` | Rust | Red Queen evolutionary optimizer — adversarial algorithm competition |
| `autonomy/` | Python | Strategy tournament, self-improving orchestration |
| `registry/` | Rust | A2A node registry server |
| `mcp/` | Python | Model Context Protocol servers |
| `aria-ui/` | TypeScript | Next.js PWA + Tauri desktop frontend |

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Manual](docs/USER_MANUAL.md) | API usage, language settings, memory system |
| [Deployment Guide](docs/DEPLOYMENT.md) | Free · VPS ($12/mo) · Cloud/k8s |
| [Contributing](CONTRIBUTING.md) | Dev setup, code standards, PR process |
| [Changelog](CHANGELOG.md) | Release history |
| [Academic Paper](docs/paper/xana_paper.md) | Full architecture paper (arXiv preprint) |

---

## Academic Paper

XANA's architecture is described in a preprint:

> **XANA: A Neuro-Symbolic Personal Cognitive AI Runtime**
> John Tapias Zarrazola — Universidad Ricardo Palma, 2026
> [arXiv:2026.XXXXX](https://arxiv.org/abs/2026.XXXXX) · [Local PDF](docs/paper/xana_paper.md)

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kemquiros/xana-core&type=Date)](https://star-history.com/#kemquiros/xana-core&Date)

---

## Contributing

PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first — key points:

- All code and comments in **English only**
- No personal data, no hardcoded secrets, no API keys in source
- Match existing code style
- Run `cd sensory && uv run python ../tests/benchmark_xana.py` and confirm XFI doesn't regress

---

## License

MIT — see [LICENSE](LICENSE).

---

Built by **[John Tapias Zarrazola](https://github.com/kemquiros)** ([@kemquiros](https://github.com/kemquiros))

*Este es mi regalo para el mundo.*
