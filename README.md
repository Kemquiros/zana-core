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

# ZANA Core

**Zarrazola Autonomous Neural Architecture**

*Local-first · Neuro-Symbolic · Evolutionary · Open Source*

[![CI](https://img.shields.io/github/actions/workflow/status/kemquiros/zana-core/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/kemquiros/zana-core/actions)
[![Release](https://img.shields.io/github/v/release/kemquiros/zana-core?style=flat-square&color=indigo)](https://github.com/kemquiros/zana-core/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)](https://python.org)
[![Rust](https://img.shields.io/badge/rust-1.78+-orange.svg?style=flat-square)](https://rustup.rs)
[![arXiv](https://img.shields.io/badge/arXiv-2026.XXXXX-b31b1b.svg?style=flat-square)](https://arxiv.org/abs/2026.XXXXX)

*"Not a chatbot. Not a wrapper. A reasoning machine that runs on your hardware."*

**ZFI (system fitness score): 100 / 100** — measured across 7 pillars with full Docker stack.

</div>

---

## TL;DR

```bash
git clone https://github.com/kemquiros/zana-core.git && cd zana-core
cp .env.example .env          # set ZANA_PRIMARY_MODEL=ollama/llama3.2:3b for fully local
docker compose up -d          # ChromaDB · PostgreSQL · Redis · Neo4j
cd sensory && uv run uvicorn multimodal_gateway:app --port 54446
curl -X POST http://localhost:54446/sense/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What do you remember about me?"}'
```

---

## Why ZANA Exists

Every AI assistant wraps an LLM and calls it intelligence.

ZANA takes a different path. It is a **cognitive runtime** — a layered architecture where neural inference, deterministic symbolic reasoning, signal processing, and adversarial evolutionary optimization work together. No single component can produce a wrong answer and have it go undetected; each layer verifies the previous one.

The name is literal: **Z**arrazola **A**utonomous **N**eural **A**rchitecture — built by one person, owned by no corporation, running on your hardware.

---

## Security (read this first)

ZANA's **Armor** middleware (Rust) runs on every request — synchronously, structurally, impossible to bypass:

```
User input → Armor::inspect_input() → Gateway → LLM → Armor::inspect_output() → Response
```

- **PII detection** — strips personal identifiers before any external model sees them
- **Prompt injection** — rejects known jailbreak patterns and adversarial payloads
- **Latency** — 2.1 µs/call (Rust); Python fallback if the `.so` is absent
- **Swarm guard** — `LLMGuard` scans peer-network rules before loading into the reasoning engine

Rejection returns HTTP 403. The LLM is never reached for blocked inputs.

---

## Use Cases

ZANA is a tool. What you build with it is limited only by your judgment and your hardware.

### 1. Personal Knowledge OS
Connect ZANA to your documents, notes, and browsing history. It ingests, indexes, and retrieves across all of them in under 50 ms. Ask cross-document questions with cited provenance. Build a second brain that actually remembers.

```bash
curl -X POST /sense/text -d '{"text": "What did I learn about Kalman filters last month?"}'
# Returns: cited recall from episodic + semantic memory
```

### 2. Autonomous Code Agent
Send a task to `/apex/orchestrate`. The Apex Quintet (5 specialized agents) decomposes it into subtasks, executes them with registered skills, verifies outputs symbolically, and delivers working code. Runs overnight.

```bash
curl -X POST /apex/orchestrate -d '{"task": "Write integration tests for the sensory module"}'
# Sentinel validates → Archivist retrieves context → Analyst decomposes
# → Operator executes → Herald delivers — all typed, no hallucination cascade
```

### 3. Business Intelligence Loop
Feed ZANA your contracts, KPIs, and market data. The CLIPS-pattern reasoning engine asserts facts, fires deterministic rules, and surfaces non-obvious strategic insights — the kind an LLM alone would miss because it predicts, not reasons.

### 4. Scientific Research Assistant
ZANA reads papers, builds a Neo4j citation graph, generates hypotheses via forward chaining, and ranks them by symbolic consistency — not just semantic similarity. It can detect logical contradictions between papers that a vector search would never find.

### 5. Document Intelligence (Legal, Medical, Financial)
Upload contracts or reports. ZANA extracts structured facts into episodic memory with timestamps and page references. Query across 1,000 documents and get answers with exact provenance — which document, which section, which date.

### 6. Voice-First Personal Assistant
```
Voice note (Telegram / PWA) → Whisper STT → Armor → Kalman → LLM → TTS response
```
No cloud STT. No cloud TTS. No data leaves your infrastructure. Works offline once models are cached.

### 7. Self-Improving Algorithm Lab (Idle Zero)
Point ZANA at a dataset. The Red Queen tournament runs 50 warrior algorithms over 2,000 generations while you sleep. The fittest cognitive algorithm is crystallized and promoted to your procedural memory. Your system improves without you touching it.

### 8. Privacy-Preserving Enterprise AI
Deploy ZANA on your VPS. Every employee query is inspected by Armor before reaching the LLM. No API key shared. No data sent to OpenAI. Full audit log of Armor rejections and agent traces. GDPR-ready by architecture.

---

## Disclaimer

**ZANA is a tool.**

Like a database, a compiler, or a programming language — it has no inherent ethical orientation. The same system that helps a researcher analyze clinical trials can be directed at other tasks by someone with different intentions.

The author (John Tapias Zarrazola) provides the instrument and publishes it under the MIT License. The responsibility for how you use it rests entirely with you.

ZANA includes an Armor layer that structurally blocks PII exfiltration and known injection patterns. This is not a moral system. It is an engineering constraint on the most common attack vectors. Misuse that falls outside those constraints is the user's responsibility.

---

## Why ZANA vs. The Market

The AI market is dominated by cloud services that predict tokens. ZANA does something structurally different.

| | **ZANA** | ChatGPT | Claude (API) | Open Interpreter | AutoGPT | LangGraph |
|---|---|---|---|---|---|---|
| **Runs locally** | ✅ 100% | ❌ Cloud | ❌ Cloud | ✅ Partial | ❌ Cloud | ⚠️ Framework |
| **Your data stays local** | ✅ | ❌ | ❌ | ✅ | ❌ | ⚠️ |
| **Symbolic reasoning layer** | ✅ CLIPS-Rust | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Security-by-architecture** | ✅ Rust Armor | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Persistent memory (4 stores)** | ✅ | ❌ Sessions | ❌ Sessions | ❌ | ⚠️ | ⚠️ |
| **Evolutionary self-improvement** | ✅ Red Queen | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Emotional modulation** | ✅ Fuzzy Heart | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Academic paper + benchmark** | ✅ ZFI/arXiv | — | — | ❌ | ❌ | ❌ |
| **Open source (auditable)** | ✅ MIT | ❌ | ❌ | ✅ MIT | ✅ MIT | ✅ MIT |
| **Cost to run** | ~$12/mo VPS | $20+/mo API | $10+/mo API | $0 (local) | Variable | Variable |

### The four differentiators no one else has

**1. Verification, not prediction.**
Every LLM output passes through a deterministic CLIPS-pattern rule engine. Facts are asserted, rules fire, contradictions surface. The symbolic layer can explain exactly why it said something — traceable to a specific rule and a specific fact. No other production AI assistant does this.

**2. Security at the system boundary.**
Armor is Rust code that executes before the LLM is invoked. It is not a Python filter added after the fact. It cannot be bypassed through prompt engineering because it runs outside the LLM's context. This matters for enterprise, for healthcare, for legal — any domain where a data breach is existential.

**3. Adversarial self-improvement.**
The Red Queen tournament (Idle Zero) evolves typed cognitive algorithms on your data while the system is idle. OpenAI retrains GPT-5 on a cluster of thousands of GPUs. ZANA improves itself on your laptop, privately, continuously, without you doing anything.

**4. Arithmetic determinism via EML.**
ZANA's Rust core uses the EML (Exponential-Log) operator as its single arithmetic primitive: every operation — multiplication, power, square root — is derived from `exp` and `log` alone. The round-trip identity `log(exp(x)) ≡ x` is verified after every signal propagation, achieving **error = 0.0** (exact IEEE-754). This makes ZANA's numerical kernel provably minimal, immune to floating-point drift, and reproducible bit-for-bit across any platform. No other personal AI runtime publicly reports this level of arithmetic determinism.

### Why choose and invest in ZANA

- **Sovereignty**: your data, your hardware, your rules — no vendor lock-in, no terms of service that can change overnight
- **Predictable cost**: $12/mo VPS vs. $0.01–0.06/1K tokens that compounds to thousands at scale
- **Auditability**: every decision is traceable — the rule that fired, the memory that was retrieved, the Armor check that passed or failed
- **Composability**: MIT license means you can fork it, extend it, embed it in your product, or build a SaaS on top — no permission needed
- **Trajectory**: the architecture is designed to scale from personal use to enterprise, from single-node to distributed swarm — the foundation is already built

---

## Capabilities

| Layer | Capability | Implementation |
|-------|-----------|---------------|
| **Sensory** | Speech-to-text | Whisper (local) |
| **Sensory** | Vision | Ollama LLaVA / Claude Vision |
| **Sensory** | Text-to-speech | edge-tts (free) |
| **Security** | PII + injection guard | Rust Armor (2.1 µs) |
| **Signal** | Uncertainty tracking | Rust Kalman (1.4 µs) |
| **Emotion** | Mood modulation | Fuzzy Heart (Mamdani inference) |
| **Memory** | Semantic recall | ChromaDB + pgvector |
| **Memory** | Episodic memory | PostgreSQL + pgvector |
| **Memory** | Procedural skills | JSON registry, RL-lite Q-values |
| **Reasoning** | Symbolic engine | CLIPS-pattern Rust, forward chaining |
| **Reasoning** | World model | Neo4j knowledge graph |
| **Evolution** | Algorithm optimization | Red Queen tournament (Idle Zero) |
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
        ├── AudioProcessor   Whisper STT
        ├── VisionProcessor  LLaVA → Claude Vision
        └── Kalman Filter    Rust Steel Core (1.4 µs)
        │
        ▼
Fuzzy Heart (emotional modulation → LLM temperature)
        │
        ▼
   Memory Query ──────────────→ Symbiosis MCP
        │                        ├── ChromaDB   (semantic)
        │                        └── PostgreSQL (episodic)
        ▼
LocalLLM (Ollama → Claude → Groq → OpenRouter)
        │
        ▼
PerceptionEvent ──→ ReasoningEngine (Rust CLIPS)
                           │
                        Neo4j World Model
                           │
                    [multi-step task?]
                           ▼
           Apex Quintet (5-agent AION protocol)
    Sentinel → Archivist → Analyst → Operator → Herald

                    [system idle?]
                           ▼
           Idle Zero — Red Queen Tournament
    Warrior algorithms evolve · Champions promoted to memory
```

---

## Quick Start

```bash
git clone https://github.com/kemquiros/zana-core.git
cd zana-core
cp .env.example .env
```

Edit `.env` — pick one LLM backend:

```bash
ZANA_PRIMARY_MODEL=ollama/llama3.2:3b        # fully local, no API key
# ANTHROPIC_API_KEY=sk-ant-...               # best reasoning quality
# OPENAI_API_KEY=sk-...                      # OpenAI-compatible
```

```bash
docker compose up -d chromadb postgres redis neo4j
cd sensory && uv run uvicorn multimodal_gateway:app --host 0.0.0.0 --port 54446
curl http://localhost:54446/health
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sense/text` | Text → PerceptionEvent + response |
| `POST` | `/sense/audio` | Audio → Whisper STT → response + TTS |
| `POST` | `/sense/vision` | Image → description + response |
| `POST` | `/sense/multimodal` | Audio + image combined |
| `WS` | `/sense/stream` | Real-time bidirectional stream |
| `POST` | `/aeon/speak` | Text → MP3 audio |
| `POST` | `/apex/orchestrate` | Multi-step task (5-agent pipeline) |
| `GET` | `/health` | System status + ZFI score |
| `GET` | `/.well-known/agent-card.json` | A2A AgentCard discovery |

---

## Building the Rust Core

```bash
cd rust_core
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
cp target/release/libxana_steel_core.so ../xana_steel_core.so
cp ../xana_steel_core.so ../sensory/xana_steel_core.so

cd ../armor
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
cp target/release/libxana_armor.so ../xana_armor.so
```

> Compiled with `target-cpu=native` (AVX2). Users on ARM or non-AVX2 x86 must remove that flag.

---

## Benchmark

```bash
cd sensory
CHROMA_HOST=localhost CHROMA_PORT=58001 \
POSTGRES_HOST=localhost POSTGRES_PORT=55433 \
REDIS_URL=redis://localhost:56380 \
NEO4J_URI=bolt://localhost:57687 \
PYTHONPATH=".." uv run python ../tests/benchmark_zana.py
```

**ZFI — ZANA Fitness Index** (7 pillars):

| Pillar | Weight | Hot Score |
|--------|--------|-----------|
| Steel Core | 20% | 100.0 |
| Memory | 20% | 100.0 |
| Symbolic Reasoning | 15% | 100.0 |
| Swarm / A2A | 15% | 100.0 |
| Market Fitness | 15% | 100.0 |
| Armor | 10% | 100.0 |
| Interoperability | 5% | 100.0 |
| **ZFI Total** | **100%** | **100.0** |

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
| `idle_zero/` | Rust | Red Queen evolutionary optimizer |
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
| [Academic Paper](docs/paper/xana_paper.tex) | Full arXiv preprint (LaTeX) |

---

## Academic Paper

> **ZANA: A Neuro-Symbolic Personal Cognitive AI Runtime**
> John Tapias Zarrazola, MsC Data Science (c) — Universidad Ricardo Palma, 2026
> [arXiv:2026.XXXXX](https://arxiv.org/abs/2026.XXXXX) · [Local source](docs/paper/xana_paper.tex)

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kemquiros/zana-core&type=Date)](https://star-history.com/#kemquiros/zana-core&Date)

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. Key rules:
- All code and comments in **English only**
- No personal data, no hardcoded secrets
- Run the benchmark — ZFI must not regress

---

## License

MIT — see [LICENSE](LICENSE).

---

Built by **[John Tapias Zarrazola](https://github.com/kemquiros)** ([@kemquiros](https://github.com/kemquiros))

*Este es mi regalo para el mundo.*
