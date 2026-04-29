# Changelog

All notable changes to ZANA Core are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [2.8.8] — 2026-04-28

### Fixed
- **Networking**: Fixed 502 Bad Gateway error by correcting the service name fallback in Caddyfile (from `pwa` to `aria-ui`).

---

## [2.8.7] — 2026-04-28

### Fixed
- **Docker Standalone**: Final fix for Aria-UI Docker build by ensuring devDependencies are present during the PostCSS/Tailwind compilation phase.
- **Global Sync**: Synchronized core and landing versions to 2.8.7.

---

## [2.8.6] — 2026-04-28

### Fixed
- **Aria-UI Build**: Fixed Docker build error where Tailwind PostCSS module was missing due to premature dev-dependency omission.
- **Frontend Persistence**: Ensured all build-time dependencies are available during the Next.js compilation phase.

---

## [2.8.5] — 2026-04-28

### Fixed
- **CLI Sync**: Explicitly bump CLI version and force uninstallation during setup to ensure the latest logic is applied.
- **Docker Visibility**: Updated `.dockerignore` to allow `.so` files, resolving the "not found" error during the COPY phase of the build.

---

## [2.8.4] — 2026-04-28

### Added
- **Diagnostic Forging**: The `zana start` command now includes a visual diagnostic layer that verifies binary integrity and repo paths before booting.

### Changed
- **Installer Security**: `install.sh` now performs a hard reset to `origin/main` to eliminate local corruption and force-reinstalls the CLI tool.

### Fixed
- **Binary Path Collision**: Resolved an issue where old/invalid shared objects were preventing Docker from seeing the newly forged Steel Core.

---

## [2.8.3] — 2026-04-28

### Fixed
- **Build System**: Improved `zana start` diagnostics to accurately resolve `STACK_ROOT` and verify Steel Core binaires.
- **Dependency Isolation**: Binary shared objects (`.so`) are no longer tracked by Git, forcing native compilation on the host for maximum compatibility.
- **Docker Context**: Fixed a critical bug where `zana_audio_dsp.so` and `zana_armor.so` were missing from the Docker build context.

---

## [2.8.2] — 2026-04-28

### Added
- **Core Projects Module**: Integrated project management directly into the cognitive core. Supports CRUD operations for projects, tasks, and files.
- **Context-per-Project**: High-performance cognitive isolation. Semantic and episodic memories are now partitioned by project ID.
- **Project-Specific Kalman Filters**: The cognitive surprise engine now maintains unique latent states per project, enabling instant context switching.
- **Rust Steel Core Extensions**: Optimized `VectorIndex` and `ProjectProcessor` modules in Rust (PyO3) for sub-millisecond validation and search.

### Fixed
- **Docker Build Flow**: Automated compilation of Rust shared objects (.so) during `zana start` and Docker image building.
- **Schema Unification**: Resolved inconsistencies between `episodes` and `episodic_memory` tables in PostgreSQL.

---

## [2.8.1] — 2026-04-27

### Fixed
- **Docker Build**: Fixed path to `pyproject.toml` and `uv.lock` in Sensory Gateway Dockerfile.
- **Dockerignore**: Allowed `.so` files to be included in the build context.
- **Dependencies**: Added missing `cryptography` and `numpy` to CLI global tool.

---

## [2.8.0] — 2026-04-27

### Added
- **ZANA Aegis Sync**: Zero-Knowledge memory synchronization engine. Uses AES-256-GCM encryption with local key derivation from a 12-word seed phrase.
- **S3 Storage Adapter**: Support for backing up the encrypted vault to any S3-compatible provider (AWS, MinIO, etc.).
- **Ars Magna 2.0**: Recursive self-criticism cycle for deep reasoning. Triggered by high Kalman surprise or user request.
- **Sync UI**: New "Memoria" tab in web settings to manage backup status and manual triggers.

### Changed
- **Orchestrator**: Refactored to be fully asynchronous, supporting parallel agent execution and non-blocking I/O.
- **Visuals**: Optimized 3D particle engine with improved shader-based audio reactivity.

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
