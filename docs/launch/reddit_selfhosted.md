# Post for r/selfhosted

**Target subreddit:** r/selfhosted (~500K members — self-hosted software, privacy, home servers)
**Best time to post:** Saturday–Sunday, 10 AM–12 PM EST (weekend browsing peaks)
**Post type:** Text post

---

## Title options

**Option A:**
> ZANA — self-hosted personal AI with persistent memory, Rust security, and zero cloud dependency [MIT]

**Option B:**
> I self-host my AI the same way I self-host my email — my data, my hardware, my rules. Here's how [MIT, Python+Rust]

**Option C:**
> After 2 years: my self-hosted AI that actually remembers things across sessions [MIT, no subscription, no accounts]

---

## Post Body

---

Hey r/selfhosted,

If you're here, you understand why self-hosting matters. I applied the same principle to AI and built [ZANA](https://github.com/Kemquiros/zana-core) — a self-hosted personal AI runtime where your memory, identity, and evolution history live on your hardware.

### Install (30 seconds)

```bash
# Linux / macOS
curl -LsSf https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.sh | sh

# Or manually
pip install vecanova-zana
zana init
zana chat
```

No Docker required to start. No accounts. No telemetry. No data leaves your machine unless you explicitly choose it.

### What makes it different from Ollama + Open WebUI

I use Ollama too — ZANA integrates with it. The difference is what ZANA adds on top:

| Feature | Ollama + WebUI | ZANA |
|---|---|---|
| Persistent memory across sessions | ❌ | ✅ SQLite FTS5, searchable |
| Memory that survives restarts | ❌ | ✅ `~/.zana/memory_lite.db` |
| PII protection at request time | ❌ | ✅ Rust armor at 2.1µs |
| Prompt injection guard | ❌ | ✅ Rust (compiled, not Python) |
| Offline capability without any model | ❌ | ✅ 15 local intents |
| Skills that evolve with usage | ❌ | ✅ WisdomRules auto-mined |
| Cryptographic reasoning audit | ❌ | ✅ SHA-256 Civic Ledger |
| Model-agnostic | Ollama only | ✅ Any LiteLLM provider |

Think of it as: Ollama handles inference, ZANA handles everything else (memory, security, identity, evolution).

### Architecture

```
~/.zana/
  memory_lite.db      ← SQLite FTS5 — all your memories, searchable
  wisdom_queue.json   ← pending skill proposals mined from your sessions
  sentinel_lite.db    ← SQLite ring buffer of all Sentinel events
  skills/             ← your local Z-Skills
    registry.json
    my-skill/
      SKILL.md
```

Everything important is local files. Portable. Backupable. No vendor lock-in.

### Self-hosting the full stack (optional)

```bash
# If you want ChromaDB + PostgreSQL + voice + web UI
zana start            # boots Docker services
zana status           # verify health
```

Services run on non-conflicting ports (54446, 54448, 55433, etc.) — designed to coexist with other self-hosted services.

### Privacy model

- **No telemetry** — there's no phone-home in the codebase (`grep -r "telemetry\|analytics\|tracking" cli/` → nothing)
- **No accounts** — `zana init` doesn't ask for email, doesn't create a user account anywhere
- **No cloud required** — Ollama + ZANA = fully local, fully air-gapped if you want
- **Open source** — MIT, read every line

### What it needs

- Python 3.12+ (the install script handles this)
- 4GB RAM minimum for Ollama
- Linux or macOS (Windows via WSL, native PowerShell installer exists but less tested)

### What's in v3.7.0 (latest)

- Herald channels: Telegram, Discord, and WhatsApp Cloud API — `zana satellite configure <platform> <token>`
- Z-Sync v1.0 — `zana zsync pull/push/status` keeps WisdomRules in sync between your machines
- The Agora — open skill marketplace with Z-Civic tamper detection
- ZANA ID — portable identity via `zaeon://` URI scheme
- 580 tests, all offline paths CI-covered

### What I'm working on next

- Android app
- True P2P WisdomRule federation (Z-Sync is currently pull/push over HTTPS)
- Windows without WSL (install.ps1 exists, needs battle-testing)

**GitHub (MIT):** https://github.com/Kemquiros/zana-core

---

**[Posting note]**: r/selfhosted appreciates practical, privacy-respecting software. Emphasize: no telemetry, no accounts, portable files, Docker is optional. Avoid the "AI changes everything" framing — they've heard it. Show the plumbing.
