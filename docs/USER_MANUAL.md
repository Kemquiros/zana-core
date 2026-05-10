# ZANA User Manual

ZANA is a personal AI cognitive system. It perceives audio, images, and text; reasons with a symbolic engine; remembers episodically; and acts through external tools — all running locally on your hardware.

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

ZANA v3.1.0 is **zero-friction**. You can start chatting in under 3 minutes without Docker.

### 1. Install the CLI

**Option A — npm (Node)**
```bash
npm install -g @vecanova/zana
zana init
```

**Option B — pipx (Python)**
```bash
pipx install vecanova-zana
zana init
```

### 2. Start your Aeon

```bash
zana chat
```
This opens the terminal chat immediately.

### 3. Full Visual Stack (Optional)
If you want the Aria UI and graph memory, you'll need Docker:
```bash
zana start
```
Then navigate to `http://localhost:54448`.

---

## Interacting with ZANA

ZANA exposes a REST + WebSocket API. You can interact via:

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

### Make ZANA speak arbitrary text

```bash
curl -X POST http://localhost:54446/aeon/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, system is ready."}'
```

Response includes `audio_b64` (base64 MP3).

---

## Interaction Language

ZANA responds in **the same language you use**. Write in Spanish → ZANA answers in Spanish. Write in English → ZANA answers in English.

Internal system code, logs, and API fields are always in English.

To change the default voice accent, set `AEON_VOICE` in `.env`:

```env
AEON_VOICE=es-CO-GonzaloNeural   # Colombian Spanish (default)
AEON_VOICE=en-US-AriaNeural      # American English
AEON_VOICE=es-MX-JorgeNeural     # Mexican Spanish
```

---

## Memory System

ZANA stores memory in multiple layers:

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

ZANA has a symbolic reasoning engine that fires rules based on asserted facts:

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

- **Input/Output armor**: All messages pass through `zana_armor.so` (Rust) for PII detection and injection prevention.
- **No credentials in code**: API keys go in `.env`, never in source files.
- **Local-first**: By default, ZANA uses local models (Ollama). Cloud APIs are only called if no local model is available and a key is set.

---

## Uninstallation Protocols

ZANA gives you complete control over your hardware and data. We offer two distinct uninstallation paths:

### 1. Sovereign Preservation (Upgrade/Transfer)
Use this if you are upgrading your hardware or moving to a different installation method.
- **What it does**: Removes the ZANA CLI and associated system binaries.
- **What it keeps**: Your `~/.zana/` directory (Aeon DNA, Ledger, Memory) remains intact.
- **Command**:
  ```bash
  # Via pipx
  pipx uninstall vecanova-zana

  # Via npm
  npm uninstall -g @vecanova/zana
  ```

### 2. Total Obliteration (Security Wipe)
Use this if you are selling your hardware or need to ensure your data is permanently removed.
- **What it does**: Removes the CLI, binaries, AND destroys all memory, DNA, and Civic Ledger files.
- **Security**: Key files (like `.env` containing API keys) are shredded before deletion.
- **Command**:
  ```bash
  bash <(curl -LsSf https://zana.vecanova.com/uninstall.sh)
  # Select option [2] and confirm with 'ZANA'
  ```

---

**Health endpoint shows backends as `not_loaded`**
→ Check that Docker services are running: `docker compose ps`

**STT not working**
→ Install: `cd sensory && uv add faster-whisper`

**TTS returns silence**
→ Install: `uv add edge-tts`

**Steel Core shows numpy fallback**
→ Build Rust core: `cd rust_core && RUSTFLAGS="-C target-cpu=native" cargo build --release --features python`
→ Then sync: `cp target/release/libzana_steel_core.so ../zana_steel_core.so && cp ../zana_steel_core.so sensory/`

**Benchmark score drops when Docker is off**
→ ChromaDB offline reduces P2 (Memory System) by ~3–4 points. Always run Docker for accurate XFI.
