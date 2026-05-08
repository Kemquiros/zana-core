<div align="center">

<img src="https://raw.githubusercontent.com/Kemquiros/zana-core/main/assets/zana_logo.svg" width="140" alt="ZANA"/>

# vecanova-zana

**Your AI doesn't remember your notes. Not a bug. Their business model.**

*ZANA is a sovereign cognitive agent that lives on your machine, remembers everything, and belongs to you — forever.*

---

[![Version](https://img.shields.io/badge/ZANA-v3.0.1-10b981?style=flat-square)](https://github.com/Kemquiros/zana-core)
[![License](https://img.shields.io/badge/License-MIT-10b981?style=flat-square)](https://github.com/Kemquiros/zana-core/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-10b981?style=flat-square)](https://pypi.org/project/vecanova-zana/)
[![Platform](https://img.shields.io/badge/Linux_·_macOS_·_Windows-555?style=flat-square)](#quick-start)

</div>

---

## The problem

Every AI session starts from zero. You re-explain your context, your preferences, your goals — every single time. Your "personal AI" remembers nothing between sessions. That's not a limitation. That's the design. They want your data on their servers.

ZANA inverts this with one architectural principle: **the memory stays with you.**

---

## Quick start

```bash
pip install vecanova-zana
zana init
zana chat
```

That's it. No Docker. No cloud account. No API key required to start.

---

## What makes ZANA different

### 4-Store Memory Architecture
ZANA maintains four types of memory simultaneously — all stored locally in `~/.zana/`:

| Store | What it holds |
|---|---|
| **Semantic** | Concepts, knowledge, domain expertise |
| **Episodic** | Conversations, events, your history |
| **Procedural** | How you solve problems, your workflows |
| **World Model** | Your mental map of projects, people, relationships |

### Aeon — Your Sovereign Agent
Every ZANA installation generates an **Aeon**: a computational identity with 35 genes derived from your usage patterns and a nanosecond-seeded entropy signature. No two Aeons are identical — not even if you reinstall.

Your Aeon evolves through 9 stages (Huevo → Fresh → Rookie → Champion → Ultimate → Legend → Archon → Mythic → Sovereign) as it absorbs your knowledge.

### Civic Ledger — Verifiable Sovereignty
Every reasoning decision ZANA makes is signed with SHA-256 and written to `~/.zana/civic_ledger.jsonl`. Open it. Read it. Verify it. Your agent can't lie to you about what it decided.

```bash
cat ~/.zana/civic_ledger.jsonl | python3 -m json.tool | head -40
```

### LLM-Agnostic by Design
Works with Claude, GPT-4, Gemini, Llama, Mistral, and any OpenAI-compatible endpoint. Switch models with one env var — your memory doesn't move.

```bash
export ZANA_PRIMARY_MODEL=claude-opus-4-7  # or gpt-4o, gemini-pro, llama3, ...
zana chat
```

### Zero-Docker, Local-First
Runs on your machine as a standard Python process. SQLite for episodic memory. No containers, no cloud sync, no telemetry.

---

## The Coliseo — Where Knowledge Becomes Combat

ZANA includes a battle engine that maps your Obsidian vault into a 6-world arena:

| World | Domain |
|---|---|
| 🔥 Ignis | Creativity, passion, vision |
| 🔢 Calculus | Logic, mathematics, systems |
| ⚒ Forge | Engineering, architecture, craft |
| 🌊 Oceanus | Strategy, flow, adaptation |
| 🌿 Sylvan | Growth, learning, philosophy |
| ∅ Void | Abstraction, chaos, emergence |

Every note you write in Obsidian shapes the terrain where your Aeon competes. Your knowledge base becomes a living arena.

---

## Z-Skill Protocol

Skills are SKILL.md files that extend ZANA's capabilities. Drop one in `~/.zana/skills/` and ZANA activates it automatically.

```bash
zana skill list      # see active skills
zana skill install   # install from registry
```

---

## Architecture

```
~/.zana/
├── aeon_dna.json       # Your agent's genetic identity
├── episodic.db         # SQLite episodic memory
├── semantic/           # Vector knowledge store
├── procedural/         # Learned workflows
├── world_model.json    # Your mental map
├── civic_ledger.jsonl  # SHA-256 audit trail
└── skills/             # Active Z-Skills
```

The core is Python. The security layer (Armor) is Rust — compiled via PyO3, zero overhead.

---

## Configuration

```bash
# ~/.zana/.env
ZANA_PRIMARY_MODEL=claude-opus-4-7
ZANA_VAULT_PATH=/home/you/Obsidian/MyVault
ZANA_LANGUAGE=en
```

Full configuration reference: [github.com/Kemquiros/zana-core#configuration](https://github.com/Kemquiros/zana-core#configuration)

---

## Requirements

- Python 3.12+
- Linux, macOS, or Windows (WSL recommended)
- 512 MB RAM minimum (2 GB recommended for large vaults)

---

## Links

- **Landing:** [zana.vecanova.com](https://zana.vecanova.com)
- **GitHub:** [github.com/Kemquiros/zana-core](https://github.com/Kemquiros/zana-core)
- **Issues:** [github.com/Kemquiros/zana-core/issues](https://github.com/Kemquiros/zana-core/issues)

---

<div align="center">

*Your data. Your hardware. Your soul.*

**JUNTOS HACEMOS TEMBLAR LOS CIELOS.**

</div>
