# Changelog

All notable changes to ZANA Core are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

---

## [2.9.11] — 2026-04-29

### Fixed
- **`zana upgrade` rewrite** — No longer requires a published GitHub Release. Checks `releases/latest` first; if absent, falls back to the latest commit SHA on `main`. On confirmation, pulls the local repo clone (`git reset --hard origin/main`) and reinstalls the CLI via `uv tool install git+...`. Closes the silent no-op that left users on outdated versions indefinitely.

---

## [2.9.10] — 2026-04-29

### Added
- **Hardware Intelligence — `zana hardware`** — New CLI command powered by [llmfit](https://github.com/AlexsJones/llmfit) (MIT). Displays a hardware panel (RAM / GPU / VRAM / CPU cores) and, with `--recommend`, shows the top N LLM models scored by quality, speed, and fit for the exact machine. `--install` auto-installs llmfit via the official installer or Homebrew. `--top N` controls result count.
- **llmfit in the model picker** — `zana setup`'s Ollama model selector now queries llmfit when available. Recommended models appear first with a `[llmfit ✓]` badge; uninstalled recommended models appear with `[pull disponible]`. If llmfit is absent, a one-line tip offers optional installation (`default=No` — zero friction). Name normalization converts llmfit display names (`Gemma 3 4B Q8_0`) to Ollama tags (`gemma3:4b`) via a lookup table + regex fallback. Fully defensive — any failure silently uses the static list.

---

## [2.9.9] — 2026-04-29

### Added
- **Sovereign Inference Wizard** — `zana setup` offers a guided 3-step Ollama configuration when no cloud API keys are entered. Step 1: pings `localhost:11434`, shows platform-specific install instructions if Ollama is not running. Step 2: lists installed models sorted by llmfit recommendation; if none exist, suggests `ollama pull gemma3:4b` and waits. Step 3: sends a real prompt to `/api/generate` and shows the live response. On success, writes `ZANA_PRIMARY_MODEL=ollama/<model>` and `OLLAMA_BASE_URL` to `~/.zana/.env`. Closes the "zombie mode" gap where ZANA responded `[Inference Error]` to every message when no keys were configured.
- **Windows / WSL Sovereignty** — Three bugs fixed in the onboarding wizard: (1) `curl | bash` TTY destruction: `_is_interactive()` check falls back to silent defaults, never aborts. (2) `;1R` ANSI escape leak: `import questionary` is now lazy — prompt_toolkit's cursor query never fires in non-TTY mode. (3) Wrong Obsidian vault path on WSL: `_is_wsl()` detects WSL via `/proc/version` and `_default_vault_path()` returns `/mnt/c/Users/<win_user>/Documents/ZANA_Vault` so Windows-side Obsidian can open it directly.
- **Rust + gcc auto-install** — `_ensure_rust_installed()` in `start.py` installs Rust via rustup if `cargo` is missing. Also detects missing C linker (`cc`/`gcc`) on apt-based systems and auto-runs `apt-get install build-essential` — without it, cargo installs successfully but fails to link binaries on fresh WSL. `install.sh` now installs both at setup time, not deferred to first boot.
- **`docs/INSTALL_WSL.md`** — Full step-by-step Windows installation guide: WSL 2 setup, Docker Desktop WSL integration, Obsidian vault path, Rust note, installer syntax, post-install verification, troubleshooting. Linked from `README.md` Quick Start and from the Windows tab in `zana-landing/Installation.tsx`.

### Changed
- **`README.md` Quick Start** — Split into Linux/macOS and Windows sections. Command corrected from `curl | bash` to `bash <(curl ...)` across both.
- **`zana-landing/Installation.tsx`** — Windows command fixed; conditional "Full Windows guide →" link appears when the Windows tab is selected.

---

## [2.9.8] — 2026-04-29

### Added
- **Transport Abstraction Layer** — `orchestrator/transport.py`. Decouples every cognitive module from its LLM provider. `BaseTransport` interface with `invoke()` / `ainvoke()` / `invoke_prompt()` / `ainvoke_prompt()`. Concrete implementations: `AnthropicTransport` (langchain-anthropic), `OllamaTransport` (httpx, zero SDK), `OpenAICompatTransport` (OpenAI SDK, covers Groq, LiteLLM, vLLM, and future sovereign endpoints). `transport_from_env(role)` factory reads `ZANA_{ROLE}_PROVIDER` + `ZANA_{ROLE}_MODEL` with `ZANA_PRIMARY_*` fallback. Strips LiteLLM-style `provider/model` prefixes automatically.
- **Per-role provider config** — `curator`, `compressor`, `orchestrator`, and `swarm` can each use a different provider via env vars. Documented in `.env.example` with sovereign model example.

### Changed
- **`curator.py`** — removed `ChatAnthropic` / `HumanMessage` direct imports; now uses `transport_from_env("curator")`.
- **`compressor.py`** — same. `_summarize()` calls `self.transport.invoke_prompt()`.
- **`graph.py`** — removed `langchain_anthropic` import. Transport is managed by sub-modules.

---

## [2.9.7] — 2026-04-29

### Added
- **Iteration Budget** — `BudgetConfig` frozen dataclass enforces hard limits on LangGraph loops. Tiers: `ZANA_MAX_ITERATIONS` (orchestrator, default 10) and `ZANA_SWARM_MAX_ITERATIONS` (per-Aeon, default 5). Features: 80% utilization warning, refundable ops that don't consume budget (`memory_read`, `semantic_search`, `context_recall`), `status_line()` telemetry on every critic tick. Budget exhaustion produces `outcome: "budget_exhausted"` in trajectory captures — providing a quality signal for model fine-tuning.
- **Tripartite outcome** in `TrajectoryCapture`: `success` / `partial` / `budget_exhausted`. Previously binary.
- **`AgentState.budget_exhausted`** — new boolean field propagated through chronicler into trajectory.

---

## [2.9.6] — 2026-04-29

### Added
- **Trajectory Capture** — Every completed Orchestrator session is now saved to `data/trajectories/`. Two formats in parallel: ZANA native JSONL (full fidelity: task, plan, observations, compression_count, outcome) and ShareGPT JSONL (compatible with LLaMA Factory, Axolotl, and most fine-tuning frameworks). Foundation for training a sovereign ZANA model on real interaction data.
- **`AgentState.task`** — New field preserves the original task string across compression cycles and LangGraph state updates.

---

## [2.9.5] — 2026-04-29

### Added
- **Context Compression** — `ContextCompressor` node injected into the LangGraph orchestrator. Automatically summarizes conversation history when total message size exceeds ~10K tokens (40K chars). Features: language-aware summaries (Spanish/English), anti-thrashing guard, graceful LLM-failure fallback. New `compressor` node routes via 3-way conditional from `critic`: task done → chronicler, context large → compressor → executor, else → executor.
- **`compression_count`** field added to `AgentState` for monitoring how many compression cycles a session has used.

---

## [2.9.4] — 2026-04-29

### Added
- **Curator Pattern** — Autonomous skill lifecycle management inspired by Hermes Agent (Nous Research). `SkillCurator` runs inside the Aeon Heartbeat (30 min cycle) and reviews procedural skills with low Q-values or prolonged inactivity. Claude Haiku attempts improvement; skills with no viable path are archived (never deleted). Curation reports persist to `claude-obsidian/wiki/curator/`.
- **Skill Lifecycle States** — `SkillRegistry` now tracks `lifecycle_state` (active / archived), `created_at`, and `last_executed` timestamps per skill. New methods: `mark_executed`, `get_stale_skills`, `archive_skill`, `get_skills_summary`.
- **Curator Obsidian Reports** — Daily JSON report of each curation cycle written to the knowledge vault.

### Fixed
- **Orchestrator Logger** — Fixed undefined `logger` reference and missing `datetime` import in `orchestrator/graph.py`.

---

## [2.9.3] — 2026-04-28

### Added
- **Diverse Aeon Visuals**: Unique 3D geometric distributions for Aeons based on forged DNA (Humanoid clusters, Cubes, Toroids, and Crystals).
- **Conversational Soul**: Dynamic LLM system prompt injection. Aeons now remember their name, archetype, and traits during conversations.
- **Interactive Sanctuaries**: Persistable Virtual Space theme switching directly from the Dashboard.

### Fixed
- **UI Depth**: Fixed z-index layering to prevent the 3D avatar from overlapping the communication channel.
- **KoruBridge Telemetry**: More graceful handling and reporting of KoruOS connection status.

---

## [2.9.2] — 2026-04-28

### Fixed
- **Networking**: Corrected `ZANA_PWA_HOST` fallback in `.env.example` and current environment, resolving the 502 Bad Gateway error when accessing through port 80.

---

## [2.9.1] — 2026-04-28

### Fixed
- **Docker Build Context**: Implemented a "Permission Doctor" in the CLI to automatically fix read issues in the `data/` directory, preventing Docker build failures.
- **Service Orchestration**: Optimized `docker-compose.yml` to use configurable data roots via `ZANA_DATA_DIR`.

---

## [2.9.0] — 2026-04-28

### Fixed
- **Docker Engine**: Robust `.dockerignore` implementation to prevent `permission denied` errors on restricted data directories.
- **CLI Ecosystem**: Version unified across all tools. Forced tool re-deployment in the installer.
- **Networking**: Final resolution of 502 Bad Gateway and Caddy-to-Aria-UI routing.

---

## [2.8.9] — 2026-04-28

### Fixed
- **Docker Permissions**: Ignored the full `data/` directory in `.dockerignore` to prevent `permission denied` errors when Caddy or Postgres create restricted files.
- **CLI Consistency**: Bumped internal CLI version to 2.8.9 to ensure update propagation.

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
