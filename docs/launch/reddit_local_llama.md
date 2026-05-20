# Post for r/LocalLLaMA

**Target subreddit:** r/LocalLLaMA (~500K members — local AI, Ollama, LLaMA, privacy-focused)
**Best time to post:** Tuesday–Thursday, 9–11 AM EST
**Post type:** Text post with code blocks

---

## Title options (A/B test)

**Option A (problem-first):**
> I built a local AI that actually remembers everything, works offline, and has a Rust security layer — after 2 years of development it's finally public [MIT]

**Option B (technical-first):**
> ZANA v3.5.0 — local AI runtime with persistent memory (SQLite FTS5), Rust PII guard at 2.1µs, and zero cloud dependency [MIT, Python+Rust]

**Option C (contrarian):**
> I was tired of ChatGPT knowing more about me than I do about myself, so I built the opposite [MIT, runs on 4GB RAM]

---

## Post Body

---

Hey r/LocalLLaMA,

Two years ago I started building what I wanted but couldn't find: an AI that runs locally, **actually remembers** everything across sessions, works offline, and has genuine security at the architecture level — not just a privacy policy.

Today I'm open-sourcing [ZANA](https://github.com/Kemquiros/zana-core) (Zero Autonomous Neural Architecture) v3.5.0 under MIT.

### What it actually does

```bash
pip install vecanova-zana
zana init       # 4 questions, then done
zana chat       # works immediately, no Docker, no accounts
```

- **Persistent memory** — SQLite FTS5 at `~/.zana/memory_lite.db`. Every conversation is indexed and searchable across sessions. `zana memory search "that idea I had about X"` works.
- **Fully offline (SPROUT tier)** — no Docker, no API key required. Uses Ollama locally. 15 offline intents (math, reminders, vault, economy, cooking, etc.) work without any model at all.
- **Rust armor layer** (`zana_armor.so`) — PII detection + prompt injection guard at **2.1 µs/request**. Compiled from source automatically on first run.
- **Exact Math Logic (EML)** — symbolic arithmetic engine in Rust that doesn't hallucinate numbers. Results are provable, not probable.
- **Civic Ledger** — every reasoning decision is SHA-256 logged. You can audit exactly why your Aeon concluded what it concluded.
- **Mastery Map** — your Aeon evolves: Seed → Larva → Warrior → Champion → Legend. WisdomRules are mined from your sessions automatically.
- **Model-agnostic** — swap with one env var: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`, Groq, Gemini, DeepSeek, anything LiteLLM supports.

### The architecture decision that matters

Most "personal AI" tools are wrappers around cloud APIs with local UI. ZANA separates **soul from compute**:

```
YOUR AEON (lives on your hardware — fully yours)
  Memory (4 stores) · Identity · Mastery Map · Civic Ledger
          │
          │  Z-Protocol (open, like HTTP)
          ▼
PROCESSING (interchangeable — no lock-in)
  Ollama · Claude · Gemini · GPT-4o · any model
```

Your Aeon is your data, your memory, your evolution history. The model is the compute engine — swap it, the Aeon stays.

### What's in v3.5.0

- **Z-Skill v1.0** — `zana skill create my-skill`, then `zana skill run my-skill "prompt"`. SKILL.md format, agentskills.io compatible.
- **Full offline command coverage** — `zana wisdom`, `zana sentinel`, `zana memory`, all work without the gateway.
- **176 tests** — every offline path is CI-tested.

### Hardware requirements

Works on a Raspberry Pi (seriously). The SPROUT tier with Ollama + Gemma 4:

| Hardware | Recommended model | Response time |
|---|---|---|
| 4GB RAM | Gemma 2B (Q4) | ~3s |
| 8GB RAM | Llama 3.1 8B (Q4) | ~1.5s |
| 16GB+ RAM | Mistral 7B or Gemma 12B | < 1s |
| M1/M2 Mac | Gemma 4 27B | real-time |

```bash
zana hardware --recommend   # auto-detects your hardware and suggests best model
```

### What's still not done (honest)

- Mobile app — not yet
- WhatsApp/Discord Herald — Telegram works, Discord in progress
- Z-Sync (Aeon federation) — the P2P WisdomRule sharing is the next major milestone
- Windows without WSL — the install.ps1 exists but hasn't been battle-tested on many machines

### Links

- GitHub (MIT): https://github.com/Kemquiros/zana-core
- PyPI: `pip install vecanova-zana`
- Paper (PDF): docs/paper/zana_paper.pdf
- Roadmap: docs/ROADMAP.md

Happy to answer questions about the architecture, the Rust integration, or the EML reasoning engine. The Civic Ledger design in particular is something I haven't seen anywhere else.

---

**[Posting note]**: Post as text. Do not include images in first version — let the architecture diagram (ASCII) speak. If the post gets traction, edit to add a GIF demo of `zana chat` in offline mode.
