# Changelog

All notable changes to ZANA Core are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [3.7.1] — 2026-05-20

### Added
- ...

### Fixed
- ...

---


## [3.7.0] — 2026-05-20 *(Sprint 12 — Herald Channels + Agora + i18n + Z-Sync + PWA)*

### Added
- **The Agora v1 — open skill marketplace** — Three new `zana skill` sub-commands:
  - `zana skill publish <name>` — Packages a local skill for Agora submission: generates `~/.zana/skills/<name>/agora_submission.json` with Z-Civic SHA-256 fingerprint, optionally opens GitHub issue URL in browser.
  - `zana skill search <query>` — Fetches remote registry from `zana-agora` GitHub and filters by name, tags, and description. Graceful offline fallback.
  - `zana skill adopt <name>` — Downloads `SKILL.md` from The Agora, verifies Z-Civic integrity (`sha256:` fingerprint), installs to `~/.zana/skills/`. Rejects tampered content before writing to disk.
  - No new runtime dependencies — network calls via stdlib `urllib`.
- **Discord Herald channel** — Full Discord Gateway WebSocket bot replacing the Sprint 9 stub:
  - Gateway connection via `websockets` + REST via `httpx` (both already in deps).
  - Routes: DMs, `/zana <prompt>` prefix in guild channels, `@mention` routing.
  - Auto-registers new Discord users on first contact (language: `en` default).
  - ZSM offline fallback when ZANA Gateway is unavailable.
  - Discord 2000-char message limit enforced.
  - `zana satellite configure discord <TOKEN>` validates the token against `/users/@me` before saving.
- **WhatsApp Herald channel** — Full WhatsApp Cloud API bot (Meta Graph API v18.0, webhook model):
  - Webhook-based message routing — Meta pushes to your endpoint; no polling loop.
  - Handles `messages`, `statuses`, and `errors` webhook objects.
  - Auto-registers new WhatsApp users on first contact.
  - ZSM offline fallback when ZANA Gateway is unavailable.
  - `zana satellite configure whatsapp <TOKEN> --phone-number-id <ID>` validates the access token via `Authorization: Bearer` header (never URL query param — prevents token leakage in proxy logs).
- **ZANA ID export/import** — `zaeon://` URI scheme for portable identity snapshots across devices.
- **6-language `zana init` wizard** — All 26 onboarding prompts translated across `es`, `en`, `pt`, `fr`, `it`, `de`. Language is auto-detected from `ZANA_LANG` env var or prompted during init.
- **Z-Sync v1.0 — WisdomRule federation over HTTPS** — `zana zsync pull/push/status` commands for syncing WisdomRules across ZANA nodes. Z-Civic SHA-256 tamper detection: modified rules are rejected before local write.
- **ARIA PWA improvements** — `aria-ui` Next.js app:
  - `InstallPrompt` component — handles `beforeinstallprompt` lifecycle with custom `BeforeInstallPromptEvent` interface. Closes banner regardless of install/dismiss outcome (prompt can only be used once). Persists dismissal to `localStorage`.
  - `appinstalled` event listener — hides banner if user installs via browser address-bar prompt, preventing stale state.
  - `viewportFit: "cover"` in Next.js `Viewport` export — required for `env(safe-area-inset-*)` to resolve to non-zero values on notched devices.
  - Safe-area CSS — `body` padding + `.bottom-safe-4` utility using `env(safe-area-inset-*)`.

### Tests
- **562 Python tests passing** — up from 212 in v3.6.0. **18 JS tests** (Jest/jsdom) for ARIA PWA.
- `cli/tests/test_skill.py` — 19 new Agora tests: `_civic_hash`, `cmd_skill_publish`, `cmd_skill_search` (query, offline), `cmd_skill_adopt` (install, civic mismatch aborts).
- `cli/tests/test_satellite.py` — 8 new Discord bot tests: DM routing, bot message ignore, guild prefix filter, slash command, auto-register.
- `cli/tests/test_zsync.py` — 24 new Z-Sync tests: `ZSyncClient.pull/push/status`, tamper detection, offline fallback, CLI wiring.
- `cli/tests/test_whatsapp.py` — 31 new WhatsApp Herald tests: `WhatsAppBot` instantiation, `validate_token` (valid/invalid/no-id edge case), `_handle_message` (new user does not touch, existing user touched), `send_message` (non-2xx log), webhook handler, foreground runner signal block, satellite CLI configure/start/status for whatsapp.
- `aria-ui/__tests__/pwa.test.ts` — 18 Jest tests: manifest required fields, icon file existence, `sw.js` event handlers, `navigator.serviceWorker.register` smoke test.

---

## [3.6.0] — 2026-05-20 *(Sprint 10 + Sprint 11 — First Dollar + Full Power Without Docker)*

### Added
- **`zana upgrade --grove`** — Interactive wizard that installs `sqlite-vec` (pip, ~2 MB, no Docker) or guides to Docker stack. Verifies the extension loads correctly after install. (`cli/zana/commands/upgrade.py:cmd_grove_upgrade()`)
- **Semantic memory without Docker (GROVE tier)** — `MemoryLiteDB` now optionally loads `sqlite-vec` for ANN vector search. `search_semantic()` auto-falls back to FTS5 if `sqlite-vec` or Ollama are unavailable. `add()` auto-indexes `zana_vault` entries when both are present. (`cli/zana/core/memory_lite.py`)
- **`zana memory reindex`** — Rebuilds the sqlite-vec vector index from all existing memories via Ollama. (`cli/zana/commands/memory.py:cmd_memory_reindex()`, `cli/zana/main.py`)
- **`is_sqlite_vec_available()` / `is_ollama_available()`** — Public helpers for feature detection without side effects. (`cli/zana/core/memory_lite.py`)
- **`zana cloud`** — Shows current tier, sqlite-vec status, and subscription tier. (`cli/zana/commands/cloud.py:cmd_cloud_status()`)
- **`zana subscribe`** — Displays $0/$8/$20 pricing table and opens browser to waitlist. No backend required for Sprint 11. (`cli/zana/commands/cloud.py:cmd_subscribe()`)
- **SPROUT tier semantic memory** — `tier.py` now reports `semantic_vault=True` for SPROUT when `sqlite-vec` is installed (previously GROVE-only). (`cli/zana/core/tier.py`)
- **`pyproject.toml [grove]` optional dep** — `pip install vecanova-zana[grove]` installs `sqlite-vec>=0.1.0`. (`cli/pyproject.toml`)
- **CONTRIBUTING.md** — No-Docker developer path, branch strategy, PR conventions, ruff + pre-commit setup. (`CONTRIBUTING.md`)
- **`docs/USER_STORIES.md`** — 16 formal user stories across 10 epics, 4 personas (Connextra + BDD), coverage matrix, DoR and DoD checklists. (`docs/USER_STORIES.md`)
- **Launch content** — Reddit and HN post drafts, competitive positioning. (`docs/launch/`)
- **CI npm version bump guard** — Prevents double-bump when `package.json` is already at target version. (`.github/workflows/ci.yml`)
- **`environment: production` on `publish-npm` job** — `NPM_TOKEN` is an environment secret; job lacked the declaration. (`.github/workflows/ci.yml`)

### Tests
- **212 tests passing** — up from 176 in v3.5.0.
- `cli/tests/test_grove_semantic.py` — 27 tests: `is_sqlite_vec_available`, `_serialize_vec`, `_get_ollama_embedding`, `has_vector_index`, `index_memory`, `search_semantic` fallback chain (no-vec, no-Ollama, full semantic), `rebuild_vector_index`, `add` auto-index.
- `cli/tests/test_upgrade_grove.py` — 6 tests: grove upgrade already-installed guard, interactive wizard flow, no-interactive flag, install failure path.
- `cli/tests/test_cloud.py` — 8 tests: `cmd_cloud_status` tier display, `cmd_subscribe` pricing table + browser open.

### Fixed
- `.npmrc` files added to `.gitignore` — prevents accidental token commits. (`.gitignore`)

---

## [3.5.0] — 2026-05-20 *(Sprint 9 — Offline Sovereignty)*

### Added
- **Z-Skill v1.0** — Local skill registry at `~/.zana/skills/`. Commands: `zana skill create <name>`, `zana skill list`, `zana skill run <name> <prompt>`, `zana skill info <name>`. SKILL.md format is agentskills.io compatible. Skills auto-register in `~/.zana/skills/registry.json`. (`cli/zana/commands/skill.py`, `cli/zana/main.py`)
- **WisdomQueue offline fallback** — All four wisdom commands now work without the Gateway. `zana wisdom inbox` reads from `~/.zana/wisdom_queue.json`. `zana wisdom approve/reject <id>` move proposals between pending/approved/rejected with atomic write (write-tmp-then-rename). `zana wisdom mine` prints an informative offline message. (`cli/zana/core/wisdom_queue.py`, `cli/zana/commands/wisdom.py`)
- **SentinelLiteDB** — SQLite ring buffer at `~/.zana/sentinel_lite.db` (max 1,000 events). `zana sentinel events` and `zana sentinel ledger` fall back to local DB when Gateway is unreachable. Ring buffer prunes oldest events automatically to keep DB bounded. (`cli/zana/core/sentinel_lite.py`, `cli/zana/commands/sentinel.py`)
- **`zana doctor --fix` — 3 new auto-fix cases**: `wisdom_queue_missing` (creates empty queue JSON), `skills_dir_missing` (creates `~/.zana/skills/` + `registry.json`), `memory_lite_corrupted` (runs `PRAGMA integrity_check` + FTS5 rebuild). (`cli/zana/commands/doctor.py`)
- **SPROUT-tier offline contract** — Every command that previously required the Gateway now has a documented offline fallback path. SEED and SPROUT tiers operate fully without Docker. (`cli/zana/commands/wisdom.py`, `cli/zana/commands/sentinel.py`)
- **`sync-release.sh` — full release flow** — Upgraded to handle `develop → release/vX.Y.Z → main → tag` automatically. Updates `README.md` version badge, auto-injects CHANGELOG template if entry missing. Flags: `--dry-run`, `--no-push`, `--hotfix`. (`scripts/sync-release.sh`)

### Tests
- **176 tests passing** across all test suites — up from 130 in v3.4.0.
- `cli/tests/test_memory_crud.py` — 26 tests: `MemoryLiteDB.delete()`, `clear()`, `export_docs()`, `import_docs()`, round-trip, CLI integration.
- `cli/tests/test_skill.py` — 19 tests: frontmatter parsing, registry CRUD, `cmd_skill_create` (valid/invalid name, duplicate guard, author field), `cmd_skill_list`, `cmd_skill_info`, `cmd_skill_run`, Typer CLI wiring.
- `cli/tests/test_sentinel_offline.py` — 12 tests: `SentinelLiteDB.record()`, `events()`, `ledger()`, `stats()`, ring buffer pruning, offline command fallbacks with mocked `httpx.ConnectError`.
- `cli/tests/test_wisdom_offline.py` — 19 tests: `WisdomQueue` load/save/roundtrip/corrupt-JSON, atomic write (no `.tmp` left), `inbox()`, `stats()`, `add()`, `approve()`, `reject()`, 4 offline command fallbacks.
- `cli/tests/test_satellite.py` — 11 tests: `load_satellite_config` / `save_satellite_config`, corrupt JSON, configure Discord, configure Telegram (valid/invalid/network error), token preservation.

### Fixed
- **Ruff lint errors in test files** — `io`, `sys`, `Path` unused imports removed from `test_memory_crud.py`; unsorted import blocks fixed in `test_wisdom_offline.py`. CI now runs `ruff check .` over all files including `cli/tests/`. (`cli/tests/test_memory_crud.py`, `cli/tests/test_wisdom_offline.py`)

---

## [3.4.0] — 2026-05-19 *(Sprint 8)*

### Added
- **`zana memory delete <id>`** — Delete a single document from local SQLite FTS5 memory by ID. Right-to-be-forgotten at record level. (`cli/zana/commands/memory.py`, `cli/zana/main.py`)
- **`zana memory clear [--collection] [--yes]`** — Bulk delete all documents, optionally scoped to one collection. Requires confirmation prompt unless `--yes` is passed. FTS5 index is rebuilt after delete. (`cli/zana/core/memory_lite.py:delete()`, `clear()`)
- **`zana memory export [--output] [--collection] [--format json|csv]`** — Export SQLite FTS5 memory to JSON (default) or CSV. Streams to stdout if no `--output` given. Enables portable Aeon backups. (`cli/zana/commands/memory.py:cmd_memory_export()`)
- **`zana memory import <file>`** — Bulk import documents from a JSON file exported by `zana memory export`. Validates format before insert. (`cli/zana/commands/memory.py:cmd_memory_import()`)
- **`memory_lite` CRUD methods** — `delete(id)`, `clear(collection)`, `export_docs(collection)`, `import_docs(docs)` added to `MemoryLiteDB`. (`cli/zana/core/memory_lite.py`)
- **ZSM intent test suite (`cli/tests/test_zsm_intents.py`)** — 44 automated tests covering all 15 ZSM intent buckets (companion, help, math, reminder, economy, language, memory, vault, cook, time, tier, aeon, ledger, skill), math result correctness, and unknown query fallback. 0% → 100% intent coverage.
- **QA runner `--local` flag (`scripts/run_qa.sh`)** — `bash run_qa.sh 3.4.0 --local` installs from local source via `pip install -e cli/` instead of failing when the version is not yet on PyPI. Resolves pre-release QA blocker.
- **MCP auto-register on `zana init`** — `_offer_mcp_registration()` in `onboarding.py` detects Claude Desktop config file (macOS/Linux/Windows paths), offers to inject the `"zana"` MCP server block, or prints the manual snippet if no config is found.
- **CI/CD restructure** — Pipeline split into 4 focused jobs: `quality` (ruff lint + format + mypy + secrets scan), `test` (pytest with coverage XML artifact), `rust` (fmt + clippy + build with Cargo cache), `release` (GitHub Release + PyPI with per-tag CHANGELOG extraction), `publish-npm`. `test` and `rust` run in parallel. (`.github/workflows/ci.yml`)
- **`scripts/sync-release.sh`** — Multi-channel release sync script (not CI). Bumps `cli/pyproject.toml`, `packages/zana-npm/package.json`, updates `zana-landing` version badges (Navbar + capabilities page), creates annotated git tag, pushes to origin. Flags: `--dry-run`, `--no-push`. Guards: semver validation, uncommitted changes check, CHANGELOG entry verification.
- **Git branching strategy** — `main` (production, PR + CI required) → `develop` (integration, CI required) → `feat/*`, `fix/*`, `hotfix/*`, `chore/*`, `release/*` (short-lived). Branch protection rules set on GitHub. All Sprint 8 work shipped via PR #1.

### Fixed
- **ZSM language lesson crash in CI** — `_exec_language_lesson()` wrote to `~/.zana/vocab_ptr_en.txt` without creating the parent directory first, causing `FileNotFoundError` in clean CI environments. Fixed with `ZANA_HOME.mkdir(parents=True, exist_ok=True)` + silent except on write failure. (`cli/zana/core/zsm.py:819`)
- **Rust `FilterMode` dead-code warning** — Variants `Precision`, `Temporal`, `Hybrid` flagged by `cargo clippy -D warnings`. Added `#[allow(dead_code)]` to preserve the public API. (`rust_core/src/kalman.rs`)
- **Rust formatting drift** — `cargo fmt -- --check` was failing in CI due to style differences in `brain.rs`, `kalman.rs`, `main.rs`, `lib.rs`, `memory.rs`, `armor/src/lib.rs`. Applied `cargo fmt` across both crates. (`rust_core/src/`, `armor/src/`)
- **Ruff UP017** — `timezone.utc` → `datetime.UTC` in 3 locations in `cli/zana/core/multiuser.py`.
- **GitHub Actions Node.js 20 deprecation** — Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as workflow-level env var to opt into Node.js 24 before the forced migration on 2026-06-02.

---

## [3.3.0] — 2026-05-19 *(Sprint 6 + Sprint 7)*

### Added
- **`zana memory add <text>`** — New CLI command that writes directly to the SQLite FTS5 store (SPROUT tier, no Docker required). Options: `--source` (label), `--collection` (namespace), `--tag` (optional metadata). Closes the "second brain" loop: `add → search → recall` now works end-to-end without any external service. (`cli/zana/commands/memory.py`, `cli/zana/main.py`)
- **REPL `/memory "<fact>"`** — The `zana chat` slash command now actually persists the fact: writes to SQLite FTS5 (`zana_vault` collection) and records an episodic entry simultaneously. Previously showed a success message but discarded the data. (`cli/zana/commands/chat.py:52-64`)
- **REPL `/query "<question>"`** — The `zana chat` slash command now performs a live FTS5 search and prints ranked results with BM25 scores inline. Previously a no-op. (`cli/zana/commands/chat.py:66-91`)
- **Security test suite (`cli/tests/test_security.py`)** — 43 automated tests covering: prompt injection (10 payloads × 2 stores), path traversal in `source` and `collection` fields (5 payloads × 2 checks), SQL/FTS5 injection (5 payloads × 2 checks), API key leakage via `stats()`, null byte handling, and 1 MB stress input. All 43 pass.
- **`zana mcp start`** — Launches the ZANA MCP memory server. Default transport: stdio (for Claude Code, Cline). Options: `--port N` (SSE transport), `--background` (daemon mode). (`cli/zana/main.py`, `mcp/zana-memory/server.py`)
- **`zana mcp config`** — Prints the ready-to-paste JSON block for `claude_desktop_config.json`. Includes config file locations for macOS, Windows, and Linux. (`cli/zana/main.py`)
- **MCP server SPROUT-compatible (`mcp/zana-memory/server.py`)** — Full rewrite with tier detection. GROVE+: `zana_steel_core` Rust vector embeddings. SPROUT (no Docker): `memory_lite` SQLite FTS5. New MCP tools: `memory_add()`, `memory_stats()`. SSE transport via `ZANA_MCP_PORT` env var. (`mcp/zana-memory/server.py`)
- **CI auto-publish PyPI** — `ci.yml` release job now runs `twine upload` automatically on every `v*.*.*` tag using `PYPI_TOKEN` secret. No more manual PyPI publish step. (`.github/workflows/ci.yml`)
- **CI auto-publish npm** — New `publish-npm` job in `ci.yml`: bumps `packages/zana-npm/package.json` version from tag, then publishes `@vecanova/zana` to npm using `NPM_TOKEN` secret. (`.github/workflows/ci.yml`)

---

## [3.2.1] — 2026-05-19

### Fixed
- **`zana --version`** — resolvía `version("zana")` (siempre fallaba → mostraba "2.0.0"). Corregido a `version("vecanova-zana")`. Detectado en QA post-release v3.2.0.

---

## [3.2.0] — 2026-05-18

### Added
- **Universal installer `scripts/install.sh`** — One-liner for Linux and macOS. Detects OS and package manager (apt/dnf/pacman/brew), installs Python 3.12 via pyenv if missing, installs pipx, installs `vecanova-zana`, and launches `zana init` automatically. Usage: `curl -LsSf https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.sh | sh`
- **Windows installer `scripts/install.ps1`** — PowerShell 5.1+/7+ script. Uses winget to install Python 3.12, then pipx, then `vecanova-zana`. Sets PATH and launches `zana init`. Usage: `irm https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.ps1 | iex`
- **`zana uninstall`** — New CLI command for controlled uninstallation. Default (partial) removes only the package. `--purge` removes package + all data directories (`~/.zana/`, `~/.local/share/com.vecanova.zana/`). Purge mode requires typing the exact phrase `eliminar zana` as an anti-typo confirmation guard. Supports `--yes` for scripted/CI usage.
- **`zana doctor --fix`** — Extends the existing audit command with interactive auto-remediation. Detects 6 fixable issues (missing LLM key, invalid vault path, pipx not found, outdated package, PATH not set, missing API key env var) and offers to fix each in-session via `typer.confirm`. Writes env vars to `~/.zana/.env` via `_upsert_env_var()`.
- **Offline memory — SQLite FTS5 (`cli/zana/core/memory_lite.py`)** — Zero-dependency local memory backend using Python's built-in SQLite FTS5. DB at `~/.zana/memory_lite.db` (WAL mode). Supports `add()`, `add_episodic()`, `search()` (BM25 ranking, score 0→1), `recall()`, `stats()`. Enables `zana memory search` and `zana memory recall` without Docker or ChromaDB.
- **`zana memory` offline fallback** — `cmd_memory_search`, `cmd_memory_recall`, and `cmd_memory_stats` now automatically fall back to SQLite FTS5 when ChromaDB/Gateway are offline (Modo Soberano / SPROUT tier).
- **Standalone binary pipeline (`.github/workflows/release-binaries.yml`)** — GitHub Actions matrix (ubuntu-22.04, windows-latest, macos-latest) builds PyInstaller `--onefile` binaries on every `v*.*.*` tag and attaches them to the GitHub Release. Artifacts: `zana-linux-x86_64`, `zana-windows-x86_64.exe`, `zana-macos-arm64`.
- **Local binary build script (`scripts/build-binary.sh`)** — Reproducible local build using the same PyInstaller flags as CI. Detects Linux/macOS, installs PyInstaller, and outputs the binary to `dist/`.
- **Real hardware detection (`zana hardware`)** — Full rewrite without `psutil`. Detects RAM via `/proc/meminfo` (Linux), `sysctl hw.memsize` (macOS), `wmic` (Windows). GPU via `nvidia-smi` or Apple Silicon arm64 detection. 14 LLM models across 5 RAM tiers with fit labels (✓ Encaja / ⚠ Justo / ✗ No alcanza). Three Rich panels with `box.ROUNDED` and `border_style="magenta"`.
- **ZSM capabilities screen in `zana chat`** — When the offline ZSM fallback activates, a Rich table with 14 intent categories is now shown, replacing the previous silent activation. Users immediately see what works without internet or LLM.
- **ZSM capabilities screen in `zana init`** — Post-wizard screen (`_render_zsm_capabilities()` in `onboarding.py`) shows the same 14 capabilities with "→ Ejecuta: zana chat" call-to-action. No longer silently hidden from new users.

### Changed
- **`zana --help`** — Description updated to `"ZANA — Zero Autonomous Neural Architecture · Works offline · No Docker required"`.
- **`README.md`** — Badge updated to v3.1.1 → v3.2.0. Platform badge: `Linux · macOS · Windows WSL` → `Linux · macOS · Windows`. Quick Start section now has 4 install methods: curl one-liner, PowerShell iex, pip manual, standalone binary download.

### Fixed
- **`zana doctor` ChromaDB tuple** — The `services` list had a 4-element entry missing the service name. Fixed to 5-element tuple: `("ChromaDB", "http", url, None, "Semantic Memory")`.

---

## [3.1.0] — 2026-05-09

### Added
- **Global Release Infrastructure** — Unified release pipeline for PyPI (`vecanova-zana`) and npm (`@vecanova/zana`).
- **Sovereign Isolation (pipx/uv)** — The CLI now promotes and enforces isolated installation via `pipx install` or `uv tool install` to prevent dependency pollution.
- **npm Wrapper v3** — New global npm installer that handles Python environment detection and isolated package deployment automatically.

### Changed
- **Module Identity Refactor** — Internal Python module renamed from `cli` to `zana` to avoid namespace collisions and align with the project's sovereign identity.
- **Unified CLI Entry Point** — The binary `zana` now consistently points to the isolated Python application across all platforms and installation methods.

---

## [2.9.15] — 2026-05-01

### Fixed
- **CLI Port Conflicts** — `zana start` now automatically detects and forcefully cleans up lingering containers from older or differently-named ZANA deployments (`zana-core`, `core-repo`) to prevent "port is already allocated" errors during initialization.

---

## [2.9.14] — 2026-04-29

### Added
- **Web Search nativo — H1 Roadmap #1** — ZANA ya no necesita salir a Google para investigar. El OPERATOR agent ahora tiene acceso a búsqueda web real con dos herramientas smolagents:
  - `web_search(query, num_results)` — busca en la web y retorna título, URL y snippet por resultado
  - `browse_url(url)` — fetcha una URL y extrae el texto limpio (HTML stripped, max 4000 chars)
  - Provider priority: **Tavily** (`TAVILY_API_KEY`) → **SearXNG** self-hosted (`SEARXNG_URL`) → **DuckDuckGo** (fallback sin clave, siempre disponible)
  - Zero nuevas dependencias obligatorias — usa `httpx` que ya estaba en el stack
- **`POST /search`** — endpoint HTTP en el Sensory Gateway (port 54446) para búsqueda desde cualquier servicio interno
- **`POST /search/browse`** — endpoint HTTP para fetch+extract de URLs
- **`GET /search/config`** — muestra qué provider está activo y qué env vars están configuradas
- **`.env.example`** — documenta `TAVILY_API_KEY` y `SEARXNG_URL` con instrucciones de setup

### Architecture
- `swarm/apex/web_tools.py` (nuevo) — `WebSearchTool`, `BrowseUrlTool`, funciones auxiliares `web_search()` y `browse_url()` compartidas con el router HTTP
- `sensory/search_router.py` (nuevo) — FastAPI router montado en `/search`
- `swarm/apex/agents.py` — `operator_agent` ahora tiene `tools=[web_search_tool, browse_url_tool]` (antes `tools=[]`)
- `sensory/multimodal_gateway.py` — monta `search_router` junto a los demás routers

---

## [2.9.13] — 2026-04-29

### Fixed
- **WSL / `curl|bash` installer crash (`Aborted.` + `;1R` escape leak)** — Three-layer fix for the onboarding wizard aborting silently when installed via `curl ... | bash` on WSL or any piped environment:
  1. **`install.sh` — `/dev/tty` reconnect**: Before invoking `zana start`, the script runs `exec < /dev/tty` to reconnect stdin to the real terminal device (canonical Unix pattern used by rustup, nvm, Homebrew). This restores the TTY for the Python onboarding wizard. If `/dev/tty` is unavailable (headless CI, Docker without TTY), automatically sets `ZANA_NON_INTERACTIVE=1` to skip prompts gracefully.
  2. **`onboarding.py` — hardened `_is_interactive()`**: The detection now uses three independent gates: CI env vars (`CI`, `DEBIAN_FRONTEND=noninteractive`, `ZANA_NON_INTERACTIVE`), `sys.stdin.isatty()`, and `termios.tcgetattr()` which catches the WSL edge case where `isatty()` reports a pseudo-terminal that `prompt_toolkit` cannot actually drive.
  3. **`onboarding.py` — `ZANA_VAULT_PATH` env var**: Power users and CI pipelines can pre-set the vault path with `ZANA_VAULT_PATH=/my/vault curl ... | bash` without any prompts.
- **`;1R` escape sequence leaking to shell**: Already fixed in v2.9.12 via lazy `questionary` import; the new `termios` gate ensures `questionary` is never imported in environments where it would trigger the `\e[6n` cursor query.

### Changed
- **Non-interactive mode now documents its escape hatch**: `install.sh` header comment documents `ZANA_NON_INTERACTIVE=1` and `ZANA_VAULT_PATH` for WSL, CI, and Docker usage.

---

## [2.9.12] — 2026-04-29

### Fixed
- **Ollama → Docker networking ("CUERPO OFFLINE")** — `zana start` now calls `_sync_user_env_to_stack()` before booting Docker. This reads `ZANA_PRIMARY_MODEL`, `OLLAMA_BASE_URL`, and all API keys from `~/.zana/.env` (written by `zana setup`) and merges them into the stack `.env` that Docker containers actually read. Critically, `OLLAMA_BASE_URL=http://localhost:11434` is rewritten to `http://host.docker.internal:11434` — `localhost` inside a Docker container resolves to the container, not the WSL/macOS host where Ollama is running. Closes the gap where a user who completed `zana setup` with Ollama still got "CUERPO OFFLINE" on every message.

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
