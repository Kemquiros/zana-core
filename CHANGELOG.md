# Changelog

All notable changes to ZANA Core are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [2.7.0] — 2026-04-26

### Added
- **Sovereign Memory Engine v2 (Rust)**: Native vector index in Rust (`memory.rs`) replacing ChromaDB. Sub-millisecond similarity search and local persistence (`data/memory.index`).
- **Ambient Senses (Voice DSP)**: Real-time passive listening via `zana_audio_dsp.so`. Passive Voice Activity Detection (VAD) and silence-triggered orchestration.
- **N8N Hardened Sandbox**: Integrated N8N into the Docker stack for secure, sovereign workflow execution and automation.
- **Cross-Aeon Protocol**: Formalized Pydantic schemas (`AeonDelegationRequest`, `AeonDelegationResponse`) for seamless task dispatching between agents and KoruOS.
- **Web-First UI (Aria)**: Aria-UI is now optimized for browser-first usage. Removed Tauri dependencies for zero-friction access from any browser.
- **Responsive UX**: Fixed Aeon avatar overlap issues on mobile and smaller screens.
- **Interactive Shadow Mode**: The "Screensaver" mode now features a "Click to Wake" overlay with backdrop blur, preventing UI lockup.

### Removed
- **ChromaDB**: Entirely removed the ChromaDB Docker service and its network dependencies to reduce system overhead and improve privacy.

---

## [1.0.0] — 2026-04-20

### Added
- Rust Steel Core: CognitiveKalmanFilter (1.4 µs/call), PolicyBrain 384→64→4 (8–10 µs), EML operator
- Rust Armor middleware: PII detection + injection prevention (2.1 µs/call)
- MultimodalGateway: audio (Whisper), vision (Claude/LLaVA), text, multimodal, WebSocket stream
- Apex Quintet: 5-agent orchestration pipeline (Sentinel, Archivist, Analyst, Operator, Herald)
- A2A interoperability: Google A2A AgentCard, Registry server (Rust), skill routing
- Procedural memory: 9 skills with RL-lite Q-values
- Distributed swarm: RemoteQuery, LLMGuard (Milestone 8.3/8.4)
- AION Protocol: typed message payloads between agents
- Docker Compose stack: ChromaDB, PostgreSQL+pgvector, Redis, Neo4j (all 5xxxx ports)
- XFI benchmark suite: 7 pillars, scoring 0–100, history log
- User Manual and Deployment Guide (Tier 1/2/3)

### XFI
- Cold (no Docker): 89.8/100
- Hot (full Docker stack): 100.0/100
