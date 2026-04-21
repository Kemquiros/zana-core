# XANA: A Neuro-Symbolic Personal Cognitive AI Runtime

**John Tapias Zarrazola**  
Maestría en Ingeniería de Sistemas  
Universidad Ricardo Palma, Lima, Perú  
`johnedisson.tapias@urp.edu.pe`

**April 2026**

---

## Abstract

We present XANA, an open-source personal cognitive AI runtime that integrates neural inference, deterministic symbolic reasoning, and multi-modal sensory processing into a unified local-first architecture. Unlike systems that wrap a large language model (LLM) with API calls, XANA maintains explicit separation between fast sub-symbolic pathways and verifiable rule-based deduction. A Rust implementation of a Kalman filter (1.4 µs/call via PyO3 zero-copy buffers) tracks epistemic uncertainty before facts enter a CLIPS-pattern forward-chaining engine. A second Rust module — Armor — inspects every input and output for personally identifiable information (PII) and adversarial prompt injection at 2.1 µs/call. Five specialized agents (the Apex Quintet) collaborate through a typed message protocol (AION) to decompose multi-step tasks without hallucination cascade. We evaluate XANA using the XANA Fitness Index (XFI), a seven-pillar composite score measuring latency, memory fidelity, reasoning correctness, agent interoperability, and security hardness. Running with a full Docker infrastructure stack, XANA achieves XFI = 100.0/100. The complete system is available at `https://github.com/kemquiros/xana-core`.

---

## 1. Introduction

The prevailing paradigm for building AI assistants is shallow: prompt a foundation model, parse the output, repeat. This approach produces systems that appear capable but are epistemically fragile. They cannot explain their inferences, forget context between sessions, and are vulnerable to adversarial inputs that exploit the absence of a verification layer.

We argue that a personal cognitive AI — one intended to augment an individual's long-term memory, reasoning, and decision-making — requires a fundamentally different architecture. Specifically, it requires:

1. **Explicit memory separation.** Episodic memories (what happened) and semantic memories (what things mean) are stored and retrieved differently. Conflating them produces recall errors and false associations.

2. **Symbolic verification.** Neural inference is probabilistic and can produce confident wrong answers. A symbolic layer that asserts structured facts and applies deterministic rules provides a second verification pass that catches and corrects neural errors.

3. **Signal uncertainty tracking.** Raw sensory input is noisy. Before facts are asserted into the symbolic engine, a signal processing stage should estimate measurement uncertainty and smooth observations over time.

4. **Security-by-architecture.** Rather than post-hoc filtering, security checks should be structural — every input and output passes through an immutable Rust layer before touching any mutable state.

XANA embodies these principles in a production-grade open-source system. This paper describes the architecture, implementation choices, and evaluation methodology.

---

## 2. Related Work

**Cognitive architectures.** Classical cognitive architectures such as ACT-R [Anderson et al., 2004] and SOAR [Laird, 2012] integrate symbolic and procedural knowledge but require hand-crafted rules and do not leverage modern neural models. XANA adapts the symbolic component (a CLIPS-inspired forward-chaining engine) to operate as a verification and augmentation layer over LLM outputs rather than as the primary reasoning substrate.

**LLM agents.** Systems such as AutoGPT [Gravitas, 2023], LangGraph [LangChain, 2024], and smolagents [HuggingFace, 2024] enable LLM-based agents to use tools and maintain state. XANA uses smolagents as the execution backend for its Apex Quintet but wraps it with a typed message protocol (AION) that prevents hallucination cascade in multi-agent chains.

**Neural-symbolic integration.** Neurosymbolic AI [Garcez & Lamb, 2023] is an active research area. Most proposed integrations train neural networks jointly with logical constraints. XANA takes a pragmatic engineering approach: neural and symbolic components are separate modules connected by a typed fact protocol, making each independently testable and replaceable.

**Security in LLM systems.** Prompt injection [Greshake et al., 2023] and PII leakage are well-documented vulnerabilities in LLM-based applications. Existing mitigations are typically implemented as Python-level string filters applied inconsistently. XANA's Armor module implements these checks in Rust at the system boundary, making them impossible to bypass through the Python application layer.

**Local-first AI.** Projects such as Ollama [Ollama, 2024] and LM Studio [LM Studio, 2024] enable running LLMs locally. XANA builds on top of local inference while adding the memory, reasoning, and security layers that raw LLM runners lack.

---

## 3. Architecture

### 3.1 Overview

XANA is organized into seven layers, each with a well-defined interface:

```
[Sensory Layer]   AudioProcessor · VisionProcessor · TextParser
      ↓
[Security Layer]  Armor (Rust) — PII scan + injection check
      ↓
[Signal Layer]    Kalman Filter (Rust Steel Core)
      ↓
[Memory Layer]    ChromaDB (semantic) · PostgreSQL (episodic) · Neo4j (world model)
      ↓
[Inference Layer] LocalLLM — Ollama / Claude / Groq / OpenRouter
      ↓
[Reasoning Layer] ReasoningEngine — CLIPS-pattern forward chaining (Rust)
      ↓
[Orchestration]   Apex Quintet — 5-agent pipeline via AION protocol
```

All inter-layer communication uses a canonical data structure — the `PerceptionEvent` — which carries the original input, extracted features, metadata, and a confidence score computed by the Kalman filter.

### 3.2 Steel Core (Rust)

The Steel Core implements two performance-critical algorithms in Rust with PyO3 bindings:

**CognitiveKalmanFilter.** Tracks a scalar state (signal quality / confidence) using a standard discrete Kalman update. The zero-copy buffer path (`update_buffer(obs)`) avoids Python-Rust memory allocation overhead and achieves 1.4 µs/call — within the ≤2 µs target for real-time sensory processing. The Python list path (`update(obs_list)`) is 4.6× slower and is provided for compatibility only.

**PolicyBrain.** A 384→64→4 feedforward network with 8-accumulator FMA (fused multiply-add) unrolling and row-major weight layout. The 8-accumulator structure hides the 5-cycle FMA latency on modern x86 CPUs. Row-major layout ensures contiguous cache access along the inner dimension.

**EML (Exponential-Log Operator).** A numerically stable identity operator `log(exp(x)) ≡ x` used for round-trip verification of signal processing pipelines. Error = 0.0.

Build command:
```bash
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
```

### 3.3 Armor (Rust Security Middleware)

Armor is a Rust shared library loaded by the Python gateway at startup. Two functions bracket every request:

- `inspect_input(payload)` — runs before the payload reaches any LLM or memory system
- `inspect_output(response)` — runs before the response is returned to the client

Both functions execute in ~2.1 µs. If either function returns a rejection signal, the gateway returns a 403 response without touching the LLM. A Python fallback (`sensory/armor_middleware.py`) is available when the Rust `.so` is absent, with higher latency and reduced detection coverage.

### 3.4 Multimodal Gateway

The gateway (`sensory/multimodal_gateway.py`) is a FastAPI application that:

1. Receives raw input (text, audio bytes, image bytes, or combinations)
2. Routes each modality to its processor (Whisper for audio, LLaVA/Claude Vision for images)
3. Calls `Armor::inspect_input`
4. Runs the Kalman filter to compute confidence
5. Queries the memory system (ChromaDB + PostgreSQL) via the Symbiosis MCP server
6. Calls the LLM with the enriched context
7. Constructs a `PerceptionEvent`
8. Passes the event to the ReasoningEngine
9. Calls `Armor::inspect_output`
10. Returns the response

This pipeline ensures that security, signal processing, memory retrieval, and symbolic verification are never skipped regardless of input modality.

### 3.5 Memory System

XANA maintains three distinct memory stores:

**Semantic memory (ChromaDB + pgvector).** Stores vector embeddings of concepts, facts, and knowledge. Retrieval uses approximate nearest-neighbor search. ChromaDB is the primary store; pgvector in PostgreSQL provides a fallback and supports complex SQL-based filtering.

**Episodic memory (PostgreSQL).** Stores timestamped records of interactions with full context. Episodic retrieval reconstructs what happened, when, and under what circumstances — distinct from semantic retrieval which answers "what does X mean."

**World model (Neo4j).** A knowledge graph that represents entities and relationships. The CLIPS-pattern engine asserts new facts into the graph as a side effect of forward chaining. The world model enables multi-hop reasoning ("if A relates to B and B relates to C, then...") that flat vector stores cannot support.

**Procedural memory.** A JSON skills registry (`procedural_memory/skills_registry.json`) stores 9 skills across 6 domains. Each skill has a Q-value updated by RL-lite (α=0.1), allowing the system to learn which skills are most useful for given task types.

### 3.6 Reasoning Engine

The ReasoningEngine implements a CLIPS-inspired forward-chaining rule system compiled to Rust. Rules are expressed as `(condition → action)` pairs operating on typed `DefTemplate` structures. The engine:

1. Receives a `PerceptionEvent` (the "initial fact set")
2. Matches all conditions across all loaded rules
3. Fires all matching rules in priority order (conflict resolution: salience-first)
4. Asserts new facts produced by fired rules
5. Repeats until no new facts are generated (fixed point)

Rules can be loaded statically (from source) or dynamically (from the Wisdom Hub peer network). Dynamic rules pass through LLMGuard (Milestone 8.4) before loading to prevent rule injection attacks.

### 3.7 Apex Quintet

For multi-step tasks, XANA deploys five specialized agents that execute sequentially:

| Agent | Role |
|-------|------|
| **Sentinel** | Validates the task request; sets scope and constraints |
| **Archivist** | Retrieves relevant context from all memory systems |
| **Analyst** | Decomposes the task into subtasks; selects tools |
| **Operator** | Executes subtasks using registered skills |
| **Herald** | Synthesizes results; formats final response |

Agents communicate exclusively through AION messages — typed Pydantic structures that carry payload type, content, confidence, and provenance. Plain-text inter-agent communication is prohibited. This eliminates the "telephone game" hallucination pattern where each agent in a chain amplifies errors from the previous one.

### 3.8 A2A Interoperability

XANA implements the Google A2A (Agent-to-Agent) protocol [Google, 2024]. An AgentCard is served at `/.well-known/agent-card.json` advertising capabilities, supported modalities, and endpoint locations. A Rust binary registry server (`registry/`) tracks active XANA nodes on the local network. This enables XANA instances to discover and query each other — the foundation for distributed swarm reasoning (Milestone 8.3).

---

## 4. Evaluation

### 4.1 XANA Fitness Index (XFI)

We define XFI as a weighted composite of seven pillars:

| Pillar | Weight | Measurement |
|--------|--------|-------------|
| Steel Core | 20% | Rust latency (Kalman + Brain) vs. targets |
| Memory | 20% | Semantic + episodic retrieval correctness |
| Symbolic Reasoning | 15% | Rule engine correctness on test fact sets |
| Swarm / A2A | 15% | Agent card discovery + inter-agent messaging |
| Market Fitness | 15% | End-to-end task completion rate |
| Armor | 10% | PII detection rate + injection rejection rate |
| Interoperability | 5% | A2A protocol compliance |

XFI = Σ(pillar_score × weight) × 100

### 4.2 Results

All measurements taken on a Linux x86-64 machine with AVX2 support, Docker stack running (hot mode):

| Component | Target | Achieved |
|-----------|--------|---------|
| Kalman (buffer path) | ≤ 2.0 µs | **1.4 µs** |
| Armor inspect | ≤ 5.0 µs | **2.1 µs** |
| PolicyBrain forward | ≤ 15 µs | **7–10 µs** |
| EML round-trip error | = 0.0 | **0.0** |
| XFI (hot, Docker up) | ≥ 90.0 | **100.0** |
| XFI (cold, no Docker) | ≥ 50.0 | **~60–70** |

### 4.3 Comparison with Existing Systems

| System | XFI-equivalent | Local-first | Symbolic layer | Security layer |
|--------|----------------|-------------|----------------|----------------|
| XANA (this work) | 100.0 | ✓ | ✓ | ✓ Rust |
| Open Interpreter | ~30 | ✓ | ✗ | ✗ |
| AutoGPT | ~33 | ✗ | ✗ | ✗ |
| Claude Code | ~41 | ✗ | ✗ | ✗ |
| N8N + AI | ~60 | partial | ✗ | partial |
| ChatGPT | ~57 | ✗ | ✗ | cloud-only |

*Note: competitor XFI scores are approximations using XANA's rubric applied to publicly documented capabilities. They are not claims made by those systems' authors.*

---

## 5. Discussion

### 5.1 Limitations

**Rust compilation.** The Steel Core and Armor modules require a local Rust toolchain. Users without AVX2 support must remove `-C target-cpu=native` or accept higher latency.

**LLM dependency.** While XANA can run with Ollama locally, best reasoning quality requires a capable LLM (Claude Sonnet or equivalent). The symbolic layer compensates for weaker local models but cannot fully substitute for a strong foundation model.

**Swarm reasoning.** Distributed reasoning across multiple XANA nodes (Milestone 8.3) is designed but not yet implemented. Current deployment is single-node.

**UI maturity.** The ARIA frontend (Next.js PWA + Tauri desktop) is functional but not production-polished.

### 5.2 Future Work

**Milestone 8.3 — Remote Swarm Query.** When the local reasoning engine has no rule covering an observed fact, the system will broadcast a `RemoteQuery` to peer nodes: "Can anyone deduce the significance of this fact?" Peer responses are scored by LLMGuard before loading.

**Milestone 8.4 — LLM Guard (in progress).** `swarm/llm_guard.py` scans dynamic rules from the Wisdom Hub for adversarial content before they enter the reasoning engine. Integration with the RemoteQuery pipeline is the primary remaining work.

**Continuous learning.** The current procedural memory uses RL-lite (α=0.1, no replay buffer). A proper experience replay mechanism would improve skill Q-value convergence.

---

## 6. Conclusion

XANA demonstrates that a personal cognitive AI can be both architecturally rigorous and practically deployable. The key contributions are:

1. A **neuro-symbolic integration pattern** where Rust Kalman filtering, LLM inference, and CLIPS-pattern forward chaining operate as sequential verification layers rather than independent pipelines.

2. A **security-by-architecture** approach where a Rust module (Armor) enforces PII and injection policies at 2.1 µs/call — below the threshold of perceptible latency and impossible to bypass through the application layer.

3. A **typed inter-agent protocol** (AION) that eliminates hallucination cascade in multi-agent chains by rejecting unstructured text as a valid message payload.

4. An **XFI evaluation framework** that scores cognitive AI systems across seven measurable pillars, providing a reproducible benchmark for future work.

The complete system — including all Rust source, Python source, Docker infrastructure, and benchmark suite — is available at `https://github.com/kemquiros/xana-core` under the MIT License.

---

## References

Anderson, J. R., et al. (2004). An integrated theory of the mind. *Psychological Review*, 111(4), 1036–1060.

Garcez, A., & Lamb, L. C. (2023). Neurosymbolic AI: The 3rd wave. *Artificial Intelligence Review*, 56, 12387–12406.

Google. (2024). Agent-to-Agent (A2A) Protocol Specification. Google LLC.

Gravitas, S. (2023). AutoGPT: An Autonomous GPT-4 Experiment. GitHub.

Greshake, K., et al. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. *AISec Workshop, ACM CCS 2023*.

HuggingFace. (2024). smolagents: A minimal framework for agentic AI. HuggingFace.

Laird, J. E. (2012). *The Soar Cognitive Architecture*. MIT Press.

LangChain. (2024). LangGraph: Building stateful, multi-actor LLM applications. LangChain Inc.

LM Studio. (2024). LM Studio: Discover, download, and run local LLMs. LM Studio Inc.

Ollama. (2024). Ollama: Get up and running with large language models locally. Ollama.

---

*Preprint — submitted to arXiv cs.AI, April 2026.*  
*Repository: `https://github.com/kemquiros/xana-core`*
