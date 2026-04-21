# XANA User Manual

XANA is a personal AI cognitive system. It perceives audio, images, and text; reasons with a symbolic engine; remembers episodically; and acts through external tools — all running locally on your hardware.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Linux / macOS / Windows (WSL2) | Ubuntu 22.04+ |
| CPU | x86-64 with AVX2 | Modern Intel/AMD (2018+) |
| RAM | 8 GB | 16 GB+ |
| Storage | 5 GB free | 20 GB (for local LLM models) |
| Docker | 24+ | latest |
| Python | 3.12+ | 3.12+ |
| Rust (optional) | 1.78+ | latest stable |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/your-org/xana-core.git
cd xana-core
cp .env.example .env
# Edit .env and fill in your API keys
```

### 2. Start the infrastructure

```bash
docker compose up -d chromadb postgres redis neo4j
```

### 3. Start the sensory gateway

```bash
cd sensory
uv run uvicorn multimodal_gateway:app --host 0.0.0.0 --port 54446
```

### 4. Verify health

```bash
curl http://localhost:54446/health
```

You should see backends listed as `online`.

---

## Interacting with XANA

XANA exposes a REST + WebSocket API. You can interact via:

- **ARIA UI** (web interface) at `http://localhost:54448`
- **Direct API calls** (see below)
- **Any HTTP client** (Postman, curl, your own app)

### Send a text message

```bash
curl -X POST http://localhost:54446/sense/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the status of my projects?", "session_id": "my-session"}'
```

### Send audio

```bash
curl -X POST http://localhost:54446/sense/audio \
  -F "audio=@/path/to/recording.wav" \
  -F "session_id=my-session" \
  -F "respond_with_audio=true"
```

### Send an image

```bash
curl -X POST http://localhost:54446/sense/vision \
  -F "media=@/path/to/screenshot.png" \
  -F "session_id=my-session"
```

### Make XANA speak arbitrary text

```bash
curl -X POST http://localhost:54446/aeon/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, system is ready."}'
```

Response includes `audio_b64` (base64 MP3).

---

## Interaction Language

XANA responds in **the same language you use**. Write in Spanish → XANA answers in Spanish. Write in English → XANA answers in English.

Internal system code, logs, and API fields are always in English.

To change the default voice accent, set `AEON_VOICE` in `.env`:

```env
AEON_VOICE=es-CO-GonzaloNeural   # Colombian Spanish (default)
AEON_VOICE=en-US-AriaNeural      # American English
AEON_VOICE=es-MX-JorgeNeural     # Mexican Spanish
```

---

## Memory System

XANA stores memory in multiple layers:

| Layer | Storage | What it holds |
|-------|---------|---------------|
| Episodic | PostgreSQL + pgvector | Past interactions, events |
| Semantic | ChromaDB | Concepts, document embeddings |
| Procedural | `procedural_memory/skills_registry.json` | Learned skills with Q-values |
| Working | Context window | Active conversation |
| World Model | Neo4j | Knowledge graph of entities |

Memory is automatically retrieved and injected into responses via the Symbiosis MCP server.

---

## Reasoning Engine

XANA has a symbolic reasoning engine that fires rules based on asserted facts:

- Facts enter via `PerceptionEvent` (sensor input)
- Rules are matched and new facts are deduced
- Conclusions trigger effects (alerts, responses, tool calls)

Rules are stored in `reasoning_engine/` and can be added via the API.

---

## Complex Tasks (Apex Quintet)

For multi-step tasks, use the orchestration endpoint:

```bash
curl -X POST http://localhost:54446/apex/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize my notes from this week and draft an action plan"}'
```

This deploys 5 specialized agents:
- **Archivist** — retrieves memory context
- **Analyst** — reasons and calculates
- **Operator** — executes external actions
- **Herald** — drafts the final response
- **Sentinel** — audits for security

---

## Security

- **Input/Output armor**: All messages pass through `xana_armor.so` (Rust) for PII detection and injection prevention.
- **No credentials in code**: API keys go in `.env`, never in source files.
- **Local-first**: By default, XANA uses local models (Ollama). Cloud APIs are only called if no local model is available and a key is set.

---

## Troubleshooting

**Health endpoint shows backends as `not_loaded`**
→ Check that Docker services are running: `docker compose ps`

**STT not working**
→ Install: `cd sensory && uv add faster-whisper`

**TTS returns silence**
→ Install: `uv add edge-tts`

**Steel Core shows numpy fallback**
→ Build Rust core: `cd rust_core && RUSTFLAGS="-C target-cpu=native" cargo build --release --features python`
→ Then sync: `cp target/release/libxana_steel_core.so ../xana_steel_core.so && cp ../xana_steel_core.so sensory/`

**Benchmark score drops when Docker is off**
→ ChromaDB offline reduces P2 (Memory System) by ~3–4 points. Always run Docker for accurate XFI.
