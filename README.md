<div align="center">

<img src="assets/zana_logo.svg" width="160" alt="ZANA Logo"/>

# ZANA Core

**Zero Autonomous Neural Architecture**

*The stable cognitive layer in a world where AI changes every six weeks.*

---

[![Version](https://img.shields.io/badge/ZANA-2.6.0--sovereign-7c3aed?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![License](https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge)](LICENSE)
[![Engine](https://img.shields.io/badge/Engine-Python_+_Rust-e879f9?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![ZFI Score](https://img.shields.io/badge/ZFI_Score-100%2F100-22c55e?style=for-the-badge)](https://github.com/kemquiros/zana-core)
[![Paper](https://img.shields.io/badge/📄_Technical_Paper-PDF-7c3aed.svg?style=for-the-badge)](docs/paper/zana_paper.pdf)

</div>

---

## 🌀 The Vision: Beyond Chatbots

Current AI systems are **rented intelligence**. They are stateless, unverified, and extractive. ZANA inverts this paradigm. It is an **External Cognitive Cortex**—a sovereign layer that inhabits your hardware, masters your context, and evolves with your life.

When Anthropic releases a new model, you don't rebuild your stack. You change one environment variable. **Your memory, your reasoning, and your rules stay with you.**

---

## 🛡️ Core Pillars

### 1. Neuro-Symbolic Integrity
ZANA fuses the fluency of Large Language Models with the deterministic rigor of symbolic logic. Every LLM output is verified by a **Rust-based forward-chaining engine** (CLIPS pattern). If the AI cannot justify a deduction through your rules, it is rejected.

### 2. The Steel Core (Rust Performance)
Performance-critical components are written in native Rust and integrated via PyO3:
*   **Cognitive Kalman Filter (1.4μs):** Tracks epistemic uncertainty and manages the context window mathematically.
*   **Armor Security (2.1μs):** Structural PII detection and injection blocking at the binary level.
*   **EML Operator:** A universal arithmetic primitive `eml(x,y) = eˣ − ln(y)` that ensures bit-level reproducibility.

### 3. 4-Store Memory System
ZANA maintains four distinct memory systems to prevent the "false association" errors common in monolithic vector databases:
*   **Semantic (ChromaDB):** Concepts, embeddings, and your knowledge vault.
*   **Episodic (PostgreSQL):** A temporal stream of every conversation and event.
*   **World Model (Neo4j):** Causal relationships and entity graphs.
*   **Procedural (JSON):** Evolved skills and champion algorithms.

### 4. Project-Centric Context
Manage multi-faceted cognitive workflows with integrated **Project Modules**. Auto-switch memory scopes, file context, and Aeon behavioral profiles based on the active mission.

---

## ⚔️ The Apex Quintet: Orchestration

ZANA coordinates a specialized squad of sub-agents communicating via the **AION Protocol** (Tensor-based resonance packets):

1.  ⚔️ **Sentinel:** Security & Anomaly Guard. Validates every input/output.
2.  📚 **Archivist:** Long-term Memory Retrieval. Compresses context.
3.  📊 **Analyst:** Logic & Inference. Executes symbolic reasoning traces.
4.  ⚙️ **Operator:** Action & Tool Execution. Interacts with the real world.
5.  📣 **Herald:** Synthesis & Reporting. The human interface.

### 🖥️ Operational Cockpit
The **Aria UI** (`/aria-ui`) is the official sensory interface. It is built with Next.js and Tauri, providing a **fully responsive**, sovereign PWA and desktop experience that connects directly to the local ZANA engine.

---

## ⚡ Installation

ZANA requires **Docker** and **Python 3.12+**.

### 🐧 Linux
```bash
curl -LsSf https://zana.vecanova.com/install.sh | bash
```

### 🍎 macOS
Requires [Homebrew](https://brew.sh/).
```bash
# Install dependencies
brew install docker docker-compose python@3.12 rustup
# Install ZANA
curl -LsSf https://zana.vecanova.com/install.sh | bash
```

### 🪟 Windows (WSL2)
Inside your WSL terminal (e.g., Ubuntu):
```bash
curl -LsSf https://zana.vecanova.com/install.sh | bash
```

---

## 🚀 Quick Start

```bash
# 1. Initialize your environment (API keys + Local LLM config)
zana setup

# 2. Boot the cognitive stack (starts Docker containers + Gateway)
zana start

# 3. Enter the REPL Cockpit
zana chat
```

> **Offline Mode:** Set `ZANA_PRIMARY_MODEL=ollama/gemma4` in your `.env` to run fully private and free with our recommended local model.

---

## 🐝 Swarm Evolution & DNA Distribution

ZANA is built for collective intelligence without central control.
*   **Red Queen Tournament:** While idle, ZANA evolves its own cognitive modules through adversarial competition.
*   **Digital DNA (SDA):** Champion modules are crystallized as *Self-Describing Architecture* packets.
*   **Z-Network (Red Z):** Export and share your evolved skills (Wisdom NFTs) with other ZANA instances via the decentralized mesh.

---

## 📄 Technical Paper

For a deep dive into the mathematical foundations, EML completeness, and Kalman-based context management, read our preprint:

[**ZANA: A Neuro-Symbolic Personal Cognitive AI Runtime (PDF)**](https://github.com/kemquiros/zana-core/blob/main/docs/paper/zana_paper.pdf)

---

## 🤝 Acknowledgements

With gratitude to: `eglejsr`, `ferchus_nandus`, `domination`, `kamo`, `virtus_sapiens`, `oma_fren`, `xanderx_monkey`.

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*

---

<div align="center">

[![Buy Me A Coffee](https://img.shields.io/badge/Support%20ZANA-Ko--fi-red?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/kemquiros)

Built with honor in Medellín, Colombia. 🇨🇴  
**[VECANOVA](https://vecanova.com)** · MIT License

</div>
