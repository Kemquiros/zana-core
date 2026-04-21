<div align="center">

```
        ▄██████████████████████▄
      ▄██████████████████████████▄
    ▄██████▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀██████▄
   ██████▀                   ▀██████
  ██████    ▄▄▄▄▄▄▄▄▄▄▄▄▄    ██████
 ██████    ████████O████████    ██████
  ██████    ▀▀▀▀▀▀▀▀▀▀▀▀▀    ██████
   ██████▄                   ▄██████
    ▀██████▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄██████▀
      ▀██████████████████████████▀
        ▀██████████████████████▀
```

# ZANA

### The cognitive layer that doesn't change when AI does.

*When Anthropic releases a new model — you change one env var.*  
*When OpenAI shifts pricing — you change one env var.*  
*Your memory, your reasoning, your rules — unchanged.*

---

[![CI](https://img.shields.io/github/actions/workflow/status/kemquiros/zana-core/ci.yml?branch=main&label=CI&style=flat-square&color=7c3aed)](https://github.com/kemquiros/zana-core/actions)
[![Release](https://img.shields.io/github/v/release/kemquiros/zana-core?style=flat-square&color=7c3aed)](https://github.com/kemquiros/zana-core/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-7c3aed.svg?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-7c3aed.svg?style=flat-square)](https://python.org)
[![Rust](https://img.shields.io/badge/rust-stable-7c3aed.svg?style=flat-square)](https://rustup.rs)
[![Paper](https://img.shields.io/badge/📄_Paper-PDF-7c3aed.svg?style=flat-square)](https://github.com/kemquiros/zana-core/blob/main/docs/paper/zana_paper.pdf)
[![ZFI](https://img.shields.io/badge/ZFI-100%2F100-22c55e.svg?style=flat-square)](docs/ROADMAP.md)

</div>

---

## Install in 30 seconds

<table>
<tr>
<td width="33%" valign="top"><b>🐧 Linux</b></td>
<td width="33%" valign="top"><b>🍎 macOS</b></td>
<td width="33%" valign="top"><b>🪟 Windows</b></td>
</tr>
<tr>
<td valign="top">

```bash
curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | sh
```

</td>
<td valign="top">

```bash
curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | sh
```

</td>
<td valign="top">

```powershell
# PowerShell (Admin) — requires WSL2
wsl curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | bash
```
Or [download the installer](https://github.com/kemquiros/zana-core/releases/latest) directly.

</td>
</tr>
</table>

Then:

```bash
zana setup       # 2-minute wizard: API keys + Docker check
zana start       # boots the full cognitive stack
zana status      # live ZFI score across 7 pillars
zana chat        # REPL connected to your Aeon
```

> **No cloud API?** → `ZANA_PRIMARY_MODEL=ollama/llama3.1:8b` → ZANA runs fully **offline and free**.

---

## The Problem

Every AI release cycle resets your tooling.  
You rebuild prompts, swap SDKs, migrate memory formats.  
The model improves. Your system regresses.

**You shouldn't have to rebuild your mind every six weeks.**

---

## What ZANA does differently

<table>
<tr><td>🧠</td><td><b>Neuro-symbolic reasoning</b></td><td>LLM outputs are verified by a CLIPS-pattern Rust engine. No rule fires without a traceable cause. No deduction without a trace.</td></tr>
<tr><td>🗃️</td><td><b>4-store memory</b></td><td>Semantic (ChromaDB) · Episodic (PostgreSQL+pgvector) · World model (Neo4j) · Procedural (JSON). Conversations persist across sessions and across models.</td></tr>
<tr><td>🛡️</td><td><b>Armor at 2.1 µs</b></td><td>Every request and response passes through a Rust PII + injection guard before any LLM sees it. Structural — not a Python filter bolted on afterward.</td></tr>
<tr><td>📐</td><td><b>Kalman context window</b></td><td>A 64-dim latent state vector tracks what the system knows and how confident it is. Context managed mathematically, not by praying your token count fits.</td></tr>
<tr><td>🔌</td><td><b>Plug&Play providers</b></td><td>Claude → GPT → Gemini → Llama (Ollama) → Groq → any LiteLLM model. One env var. Zero code changes.</td></tr>
<tr><td>⚔️</td><td><b>Aeon Fleet</b></td><td>8 specialized agents. You pick which one handles a task, or ZANA recommends based on context.</td></tr>
<tr><td>🐝</td><td><b>Swarm evolution</b></td><td>Red Queen bootstraps warrior Aeons that evolve their cognitive DNA autonomously via meta-evolutionary optimization.</td></tr>
<tr><td>🌐</td><td><b>Runs everywhere</b></td><td>Terminal · PWA · Desktop (Tauri) · Telegram · Slack · Discord. Same cognitive runtime on every surface.</td></tr>
</table>

---

## Quick Start

```bash
# 1. Choose your LLM provider (ONE line)
echo 'ZANA_PRIMARY_MODEL=anthropic/claude-3-5-haiku-20241022' >> .env   # Claude (fastest)
echo 'ZANA_PRIMARY_MODEL=openai/gpt-4o-mini'                 >> .env   # GPT
echo 'ZANA_PRIMARY_MODEL=gemini/gemini-1.5-flash'            >> .env   # Gemini
echo 'ZANA_PRIMARY_MODEL=ollama/llama3.1:8b'                 >> .env   # Local — FREE

# 2. Start the stack
zana start

# 3. Talk
zana chat
> What did I ask you about yesterday?
> Analyze this error and remember the fix: [paste stack trace]
> Remember: the client demo is on Friday at 3pm
```

---

## What can you build?

<table>
<thead><tr><th>Use Case</th><th>How</th><th>Aeon</th></tr></thead>
<tbody>
<tr><td>🔍 <b>Personal knowledge base</b></td><td><code>zana embed ~/notes/</code> → ask anything across your entire vault</td><td>Archivist</td></tr>
<tr><td>💻 <b>Dev assistant with memory</b></td><td>Connects to your codebase. Remembers your architecture decisions across sessions.</td><td>Forge</td></tr>
<tr><td>📊 <b>Business intelligence</b></td><td>Feed structured facts → symbolic rules fire → <code>LOCK_EXPENSES</code>, <code>ALERT_TEAM</code></td><td>Analyst</td></tr>
<tr><td>🔐 <b>Security monitoring</b></td><td>Every event passes Armor + reasoning engine. Anomalies trigger defined effects.</td><td>Sentinel</td></tr>
<tr><td>📚 <b>Research assistant</b></td><td>Upload papers → semantic search → episodic recall of your readings over time</td><td>Scholar</td></tr>
<tr><td>🤖 <b>Automation layer</b></td><td>Webhook → <code>/sense/text</code> → reasoning → effect → external action pipeline</td><td>Operator</td></tr>
<tr><td>👁️ <b>Visual intelligence</b></td><td>Screenshot → <code>/sense/vision</code> → description + entities + Aeon response</td><td>Watcher</td></tr>
<tr><td>💬 <b>Team AI bot</b></td><td>Add to Slack/Discord/Telegram. One ZANA per team, shared persistent memory.</td><td>Herald</td></tr>
</tbody>
</table>

---

## Aeon Fleet

Eight specialized cognitive agents. Each with its own model, cost tier, and toolset.

| Aeon | Role | Default Model | Cost |
|------|------|---------------|------|
| ⚔️ **Sentinel** | Security audit · anomaly detection | claude-haiku | 🟢 Low |
| 📚 **Archivist** | Semantic memory · document retrieval | claude-haiku | 🟢 Low |
| 📊 **Analyst** | Data reasoning · symbolic inference | claude-sonnet | 🟡 Mid |
| ⚙️ **Operator** | Code execution · external actions | claude-sonnet | 🟡 Mid |
| 📣 **Herald** | Communication · report generation | claude-haiku | 🟢 Low |
| 🔨 **Forge** | Code generation · architecture design | claude-opus | 🔴 High |
| 🎓 **Scholar** | Research · long-form synthesis | claude-opus | 🔴 High |
| 👁️ **Watcher** | Vision · multimodal · monitoring | claude-sonnet | 🟡 Mid |

```bash
zana aeon list                                 # full fleet with status
zana aeon use forge                            # switch Aeon for this session
zana aeon recommend "analyze this dataset"     # ZANA picks the right one
```

> Every Aeon's model is independently configurable. `FORGE_MODEL=ollama/llama3.1:70b` → Forge runs locally.

---

## Swap your LLM in 5 seconds

```bash
# .env — one variable, restart, done. No code changes.

ZANA_PRIMARY_MODEL=anthropic/claude-3-5-haiku-20241022   # Claude Haiku
ZANA_PRIMARY_MODEL=anthropic/claude-opus-4-7             # Claude Opus (most capable)
ZANA_PRIMARY_MODEL=openai/gpt-4o                         # GPT-4o
ZANA_PRIMARY_MODEL=gemini/gemini-1.5-pro                 # Gemini Pro
ZANA_PRIMARY_MODEL=groq/llama-3.1-70b-versatile          # Groq (ultra-fast)
ZANA_PRIMARY_MODEL=ollama/llama3.1:8b                    # Local, free, 100% private
ZANA_PRIMARY_MODEL=ollama/mistral:7b                     # Local, lightweight
```

LiteLLM resolves the provider from the model prefix. ZANA doesn't know which one you picked — and it doesn't need to.

---

## Connect everything

```bash
# Telegram (personal assistant)
TELEGRAM_BOT_TOKEN=<from @BotFather> python -m telegram_bot.bot

# Slack (team workspace)
SLACK_BOT_TOKEN=<xoxb-...> SLACK_APP_TOKEN=<xapp-...> python mcp/zana-slack/bot.py

# Discord (community)
DISCORD_BOT_TOKEN=<token> python mcp/zana-discord/bot.py
# Slash commands: /sense /reason /recall /status /swarm /aeon

# PWA (mobile & web — installable)
open http://localhost:54448

# Desktop app
# → Download .deb / .AppImage / .dmg / .msi from GitHub Releases
```

### MCP Integration (Claude Code / Claude Desktop)

Drop ZANA's cognitive tools directly into any MCP-compatible client:

```json
{
  "mcpServers": {
    "zana-memory":   { "command": "uv", "args": ["run", "--directory", "mcp/zana-memory",   "python", "server.py"] },
    "zana-episodic": { "command": "uv", "args": ["run", "--directory", "mcp/zana-episodic", "python", "server.py"] },
    "zana-slack":    { "command": "uv", "args": ["run", "--directory", "mcp/zana-slack",    "python", "server.py"] },
    "zana-discord":  { "command": "uv", "args": ["run", "--directory", "mcp/zana-discord",  "python", "server.py"] }
  }
}
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       INPUT SURFACES                          │
│   Terminal · PWA · Desktop · Telegram · Slack · Discord      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │   ARMOR  (Rust)    │  ← PII + injection @ 2.1µs
                  └─────────┬──────────┘
                            │
            ┌───────────────▼────────────────┐
            │    SENSORY GATEWAY  :54446      │
            │    Audio · Vision · Text · WS   │
            │    LiteLLM Router               │
            │    Claude/GPT/Gemini/Ollama/Groq │
            └──────┬──────────────────┬───────┘
                   │                  │
      ┌────────────▼────┐   ┌─────────▼───────────┐
      │  KALMAN FILTER  │   │  REASONING ENGINE    │
      │  steel_core.so  │   │  CLIPS-Rust fwd-chain│
      │  64-dim latent  │   │  + Wisdom Hub sync   │
      └────────────┬────┘   └─────────┬────────────┘
                   │                  │
      ┌────────────▼──────────────────▼────────────┐
      │                 4-STORE MEMORY              │
      │  ChromaDB    PostgreSQL+pgvector    Neo4j   │
      │  Semantic    Episodic               World   │
      │  (vault)     (conversations)        (graph) │
      └─────────────────────┬──────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │    AEON FLEET      │  ← 8 specialized agents
                  │    RED QUEEN       │  ← Evolutionary swarm
                  └────────────────────┘
```

---

## Power User CLI

```bash
# Full system audit
zana doctor

# Memory — query across all 4 stores
zana memory search "decisions made in Q1"
zana memory recall 20
zana memory stats

# Symbolic reasoning — manual forward-chaining
zana reason machine_health_avg=0.3
zana reason last_action_status=FAILED --remote   # ask the swarm

# Swarm — Red Queen evolutionary fleet
zana swarm init --warriors 50 --generations 2000
zana swarm status --watch                         # live dashboard
zana swarm sync                                   # pull Wisdom Hub rules
zana swarm query machine_health_avg

# Shadow Observer — silent background meta-evolution
zana shadow enable
zana shadow status
```

---

## The Paper

ZANA is backed by 33 pages of technical depth: the neuro-symbolic architecture, the EML universal arithmetic operator (`eml(x,y) = eˣ − ln(y)`), Kalman-based context management, the ZFI evaluation framework, and comparative benchmarks.

<div align="center">

[![📄 Read the Paper — PDF](https://img.shields.io/badge/📄_Read_the_Paper-33_pages,_PDF-7c3aed?style=for-the-badge)](https://github.com/kemquiros/zana-core/blob/main/docs/paper/zana_paper.pdf)

*Available directly on GitHub while arXiv review is pending.*

</div>

---

## ZFI — ZANA Fitness Index

Seven measurable pillars. Fully reproducible benchmark included.

| Pillar | Weight | Measures |
|--------|--------|----------|
| Gateway | 30 pts | Sensory pipeline latency + availability |
| Semantic Memory | 20 pts | ChromaDB response + collection health |
| Episodic Memory | 15 pts | PostgreSQL latency + record integrity |
| Cache | 10 pts | Redis hit rate + response time |
| World Model | 15 pts | Neo4j query latency + graph integrity |
| Interface | 10 pts | PWA availability + load time |
| **Total** | **100 pts** | |

**Hot (full Docker stack): 100 / 100**  
**Cold (no Docker, Gateway only): 89.8 / 100**

```bash
zana status        # current score
zana doctor        # full audit, latency per pillar
```

---

## Manifesto

We built ZANA because we believe the most dangerous dependency in 2025 is a dependency on a single AI provider.

Not because they're untrustworthy — because they're *changing too fast*. Every six weeks a new model. Every quarter a new API. Every year a new paradigm. If your intelligence layer sits directly on top of any one provider, you're one announcement away from refactoring your entire system.

**Cognitive sovereignty means your reasoning is yours.**  
Your memory doesn't live on someone else's server.  
Your rules don't reset when you upgrade.  
Your context doesn't disappear when a conversation ends.

ZANA is the stable ground beneath the chaos — a deterministic symbolic layer that verifies neural outputs, a memory system that persists across models and years, a security layer that doesn't ask the LLM for permission.

You own your Aeon. You own its memory. You own its rules.  
The LLM is just a voice. And you choose which voice speaks.

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*

---

## Stack

| Layer | Technology |
|-------|-----------|
| Cognitive runtime | Python 3.12 + Rust stable |
| LLM routing | LiteLLM — Claude · GPT · Gemini · Groq · Ollama |
| Reasoning | CLIPS-pattern forward-chaining in Rust |
| Context management | Kalman filter (Steel Core.so, 1.4 µs) |
| Security | Armor.so (Rust, 2.1 µs/call) |
| Semantic memory | ChromaDB + sentence-transformers |
| Episodic memory | PostgreSQL 16 + pgvector |
| World model | Neo4j 5 |
| Cache | Redis 7 |
| Audio | faster-whisper (STT) + edge-tts (TTS) |
| Vision | Claude Vision / LLaVA via Ollama |
| Desktop | Tauri v2 (Rust + Next.js 15) |
| PWA | Next.js 15 + Framer Motion |
| MCP | FastMCP — memory · episodic · world · Slack · Discord |
| Reverse proxy | Caddy 2 (automatic HTTPS) |
| Container | Docker Compose |

---

## Self-hosting in 5 minutes

```bash
git clone https://github.com/kemquiros/zana-core.git && cd zana-core
cp .env.example .env
# Edit .env — set at least ONE API key or OLLAMA_BASE_URL for local LLM
docker compose up -d
zana doctor   # → ZFI 100/100
```

**Requirements:** Docker 24+, 4 GB RAM, 10 GB disk.  
Supports x86_64 and ARM64 (Apple Silicon, Raspberry Pi 4+).

---

## Contributing

```bash
# Run tests
cd sensory && uv run pytest ../tests/ -v

# Benchmark
cd sensory && uv run python ../tests/benchmark_zana.py

# Lint
cd rust_core && cargo check
cd armor      && cargo check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Acknowledgements

ZANA was conceived, designed, and built by **John Tapias** ([@kemquiros](https://github.com/kemquiros)) — Medellín, Colombia. [VECANOVA](https://vecanova.com).

With gratitude to those who showed up in the dark hours:

| | |
|---|---|
| **eglejsr** | Grounding. The first to believe this wasn't just code. |
| **ferchus_nandus** | Endurance. Proved that discipline and love are not opposites. |
| **domination** | Precision. Demanded nothing less than the real thing. |
| **kamo** | Clarity. Knew what mattered before I did. |
| **virtus_sapiens** | Wisdom. The kind that comes from choosing difficulty on purpose. |
| **oma_fren** | Origin. Everything before the complexity. |
| **xanderx_monkey** | Chaos. The kind that breaks you open, not down. |

---

<div align="center">

**[📄 Paper](https://github.com/kemquiros/zana-core/blob/main/docs/paper/zana_paper.pdf) · [🗺️ Roadmap](docs/ROADMAP.md) · [🐛 Issues](https://github.com/kemquiros/zana-core/issues) · [📦 Releases](https://github.com/kemquiros/zana-core/releases)**

<br>

*Not a chatbot. Not a wrapper. A reasoning machine that runs on your hardware.*

<br>

MIT License · Built with honor in Medellín, Colombia.

</div>
