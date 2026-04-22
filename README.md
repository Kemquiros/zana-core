<div align="center">

<img src="../assets/zana_logo.svg" width="160" alt="ZANA Logo"/>

# ZANA Core

**Zero Autonomous Neural Architecture**

*The stable cognitive layer in a world where AI changes every six weeks.*

---

[![Version](https://img.shields.io/badge/ZANA-2.0.0--Stable-7c3aed?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![License](https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge)](LICENSE)
[![Engine](https://img.shields.io/badge/Engine-Python_+_Rust-e879f9?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![ZFI Score](https://img.shields.io/badge/ZFI_Score-100%2F100-22c55e?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![Paper](https://img.shields.io/badge/📄_Technical_Paper-PDF-7c3aed.svg?style=for-the-badge)](docs/paper/zana_paper.pdf)

</div>

---

## The Problem

The AI landscape changes every six weeks. GPT-4 → Claude 3.5 → Gemini 2.0 → whatever ships tomorrow. Each migration breaks your stack, erases your context, and resets your workflow.

You're **renting intelligence** from corporations. Your conversation history lives on their servers. When they change the API, deprecate the model, or raise the price — you start over.

There's no stable layer you control.

## The Solution

ZANA is a **sovereign cognitive runtime** you own completely. It sits between you and the entire AI ecosystem as a permanent, stable infrastructure layer.

```
┌──────────────────────────────────────────────────────────────────┐
│         AI ECOSYSTEM  (changes constantly)                       │
│   Claude · GPT-4o · Gemini · Llama · Mistral · [next model]     │
└───────────────────────────┬──────────────────────────────────────┘
                            │  one config line switches providers
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Z A N A                                   │
│                                                                  │
│  Permanent memory  ·  Symbolic reasoning  ·  Aeon fleet         │
│  Rust armor        ·  Bayesian filtering  ·  Your hardware      │
└──────────────────────────────────────────────────────────────────┘
```

Switch from Claude to Gemini: **one env var**. Your memory, your Aeons, your reasoning — unchanged.

---

## Install

```bash
curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | sh
```

Or with `uv`:

```bash
uv tool install zana
```

---

## Quick Start

```bash
zana setup      # configure API keys (interactive wizard)
zana start      # boot the full stack
zana status     # verify all services + ZFI score
zana chat       # talk to your ZANA
```

---

## Your Aeon Fleet

ZANA orchestrates a fleet of specialized cognitive agents. Each Aeon is optimized for a specific class of task. ZANA recommends the right one based on context — or you choose manually.

| Aeon | Role | Best for |
|---|---|---|
| 📢 **Herald** | Synthesis & output | General conversation, summaries, writing |
| 🔨 **Forge** | Software engineering | Code, architecture, refactoring, tests |
| 🔬 **Analyst** | Logic & math | Reasoning, proofs, data analysis |
| 📚 **Archivist** | Memory & retrieval | Search, recall, knowledge retrieval |
| 🎓 **Scholar** | Deep research | Papers, literature, long synthesis |
| ⚙️ **Operator** | World execution | Run commands, deploy, API calls |
| 🛡 **Sentinel** | Security | PII detection, injection guard, compliance |
| 👁 **Watcher** | Passive context | Background monitoring, alerts |

---

## Architecture

### The Four Pillars

**1. Bayesian Filtering — Kalman-Induced Memory**

Standard RAG floods context with noise. ZANA treats context as a **Latent State Vector**. The `CognitiveKalmanFilter` (Rust, 1.4µs) compresses low-signal data and preserves the context window for high-uncertainty stimuli.

**2. EML Symbolic Grounding — Zero Hallucination**

Mathematical reasoning is grounded via the **Exp-Minus-Log operator**:
`eml(x, y) = eˣ − ln(y)`

Any continuous elementary function is representable as a binary tree of this single operation — exact symbolic regression, no approximation.

**3. 4-Store Memory — Nothing Gets Lost**

*   **Semantic** (ChromaDB): Concepts, embeddings, vault.
*   **Episodic** (PostgreSQL + pgvector): Conversations, timelines.
*   **World model** (Neo4j): Causal relationships, entities.
*   **Procedural** (JSON registry): Skills, tools, workflows.

**4. Armor Layer — Structural Security**

Rust middleware at 2.1µs. PII interception and injection blocking happen at the hardware layer — before any Python code runs, before any LLM sees the input.

---

## 7-Layer Cognitive Stack

1.  **SENSORY**: Whisper (audio) + LLaVA (vision) + text.
2.  **ARMOR**: Rust PII + injection guard (2.1µs).
3.  **SIGNAL**: Kalman Filter (1.4µs) + Fuzzy Heart.
4.  **MEMORY**: 4-store: ChromaDB/Postgres/Neo4j/JSON.
5.  **INFERENCE**: LiteLLM router → any LLM provider.
6.  **REASONING**: CLIPS forward-chaining (Rust engine).
7.  **ORCHESTRATION**: Apex Quintet (5 specialized sub-agents).

---

## ZFI Benchmark

**ZANA Fitness Index** — 7-pillar composite score across latency, memory, reasoning, security, autonomy, adaptability, and sovereignty.

*   Cold (no Docker): **89.8 / 100**
*   Hot (full stack): **100.0 / 100**

---

## Infrastructure Stack

*   **Engine**: Python 3.12 (orchestration) + Rust Steel Core (Kalman, EML, Armor — PyO3).
*   **Memory**: ChromaDB (Semantic), PostgreSQL (Episodic), Redis (Cache), Neo4j (World Model).
*   **LLM Layer**: LiteLLM (Anthropic / OpenAI / Gemini / Groq).
*   **Interfaces**: ZANA-UI (Next.js 16), Desktop (Tauri v2), CLI (zana).

---

## Acknowledgements

To those who believed when there was nothing yet to see: `eglejsr`, `ferchus_nandus`, `domination`, `kamo`, `virtus_sapiens`, `oma_fren`, `xanderx_monkey`.

> *The empire is built on the shoulders of those who said "I believe" before the architecture existed.*

---

<div align="center">

*WE MAKE THE HEAVENS TREMBLE.*

**VECANOVA** · Built by [John Tapias](https://github.com/kemquiros)

</div>
