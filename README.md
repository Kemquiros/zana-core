# XANA Core

**XANA** is a multimodal cognitive AI system. It perceives audio, images, and text; reasons with a Bayesian-symbolic engine; remembers across sessions; and acts through external tools — all running locally on your hardware.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Rust](https://img.shields.io/badge/rust-1.78+-orange.svg)](https://rustup.rs)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)

---

## What XANA Does

| Capability | How |
|---|---|
| Speech-to-text | Whisper (local, no API required) |
| Vision analysis | Claude Vision or Ollama LLaVA |
| Text-to-speech | edge-tts (Microsoft Azure, free tier) |
| Semantic memory | ChromaDB + pgvector |
| Symbolic reasoning | CLIPS-pattern rule engine in Rust |
| Kalman filtering | Rust Steel Core (1.4 µs/call) |
| Multi-agent tasks | 5-agent Apex Quintet (smolagents) |
| A2A interoperability | Google A2A protocol (AgentCard) |
| Security | Rust Armor middleware (PII + injection detection) |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+

### 1. Configure

```bash
git clone https://github.com/your-org/xana-core.git
cd xana-core
cp .env.example .env
# Fill in at least one API key (or set XANA_PRIMARY_MODEL=ollama/llama3.2:3b for fully local)
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

### 4. Verify

```bash
curl http://localhost:54446/health
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sense/text` | Text → PerceptionEvent + response |
| POST | `/sense/audio` | Audio file → STT → response + TTS |
| POST | `/sense/vision` | Image/video → description + response |
| POST | `/sense/multimodal` | Audio + image combined |
| WS | `/sense/stream` | Real-time bidirectional stream |
| POST | `/aeon/speak` | Arbitrary text → MP3 audio |
| POST | `/apex/orchestrate` | Complex multi-step task (5-agent pipeline) |
| GET | `/health` | Backend status |
| GET | `/.well-known/agent-card.json` | A2A AgentCard |

---

## Architecture

```
User Input (text / audio / image)
        │
        ▼
MultimodalGateway  ←── Armor (Rust, PII + injection check)
        │
        ├── AudioProcessor  (Whisper STT + DSP features)
        ├── VisionProcessor (Ollama LLaVA → Claude Vision)
        ├── Kalman Filter   (Rust Steel Core, 1.4 µs)
        │
        ▼
Cortex query  ─────────→  Symbiosis MCP Server
        │                         │
        │                   ┌─────┴─────┐
        │               ChromaDB    PostgreSQL
        │              (semantic)  (episodic)
        ▼
LocalLLM (Ollama → Claude → Groq → OpenRouter)
        │
        ▼
PerceptionEvent  ──→  ReasoningEngine (Rust CLIPS)
                              │
                         Neo4j World Model
```

For multi-step tasks, `/apex/orchestrate` deploys:
**Sentinel → Archivist → Analyst → Operator → Herald → Sentinel**

---

## Modules

| Module | Language | Purpose |
|--------|----------|---------|
| `sensory/` | Python | Multimodal gateway, STT, TTS, vision |
| `rust_core/` | Rust | Kalman filter, policy brain, EML operator |
| `armor/` | Rust | Security middleware (PII, injection) |
| `reasoning_engine/` | Python/Rust | Symbolic rule engine |
| `swarm/` | Python | A2A protocol, Apex Quintet agents |
| `episodic/` | Python | Episodic memory (PostgreSQL) |
| `world_model/` | Python | Neo4j knowledge graph |
| `procedural_memory/` | Python | Skills registry with RL-lite Q-values |
| `registry/` | Rust | A2A node registry server |
| `mcp/` | Python | Model Context Protocol servers |
| `aria-ui/` | TypeScript | Next.js PWA frontend |

---

## Building the Rust Core

The Steel Core provides sub-microsecond inference. Requires Rust 1.78+ with PyO3:

```bash
cd rust_core
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python

# Sync the .so to both required locations
cp target/release/libxana_steel_core.so ../xana_steel_core.so
cp ../xana_steel_core.so ../sensory/xana_steel_core.so
```

---

## Running the Benchmark

```bash
cd sensory
CHROMA_HOST=localhost CHROMA_PORT=58001 \
POSTGRES_HOST=localhost POSTGRES_PORT=55433 \
REDIS_URL=redis://localhost:56380 \
NEO4J_URI=bolt://localhost:57687 \
PYTHONPATH=".." uv run python ../tests/benchmark_xana.py
```

XFI (XANA Fitness Index) measures 7 pillars: Steel Core, Memory, Symbolic Reasoning, Swarm, A2A, Market Fitness, and Armor. Full Docker stack scores 100/100.

---

## Documentation

- [User Manual](docs/USER_MANUAL.md) — Getting started, API usage, language settings
- [Deployment Guide](docs/DEPLOYMENT.md) — Free/VPS/Cloud tiers with cost estimates
- [Contributing](CONTRIBUTING.md) — How to contribute

---

## License

MIT — see [LICENSE](LICENSE).
