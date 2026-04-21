# Changelog

All notable changes to ZANA Core are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

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
