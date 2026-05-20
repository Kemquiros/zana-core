# ZANA Public Launch Checklist

**Target launch date:** 2026-05-20+
**Version to launch:** v3.7.0

Run this checklist top-to-bottom before posting anywhere.

---

## Pre-launch: Code

- [ ] `pip install vecanova-zana==3.7.0` succeeds on a clean machine
- [ ] `zana init` completes without errors (≤4 questions)
- [ ] `zana chat` responds without Docker running
- [ ] `zana hardware --recommend` returns output
- [ ] `curl -LsSf .../install.sh | sh` works on Ubuntu 22.04 (test in VM or Docker)
- [ ] GitHub Release `v3.7.0` exists with CHANGELOG notes attached
- [ ] PyPI page shows v3.7.0 as latest: https://pypi.org/project/vecanova-zana/

## Pre-launch: Repository

- [ ] README version badge shows v3.7.0
- [ ] README has no Spanish text
- [ ] README Quick Start: SPROUT path (no Docker) is shown FIRST
- [ ] CONTRIBUTING.md: dev setup works with `pip install -e "cli/[dev]"` + `pytest`
- [ ] GitHub repo has description set
- [ ] GitHub repo has topics set: `ai`, `personal-ai`, `local-llm`, `python`, `rust`, `cli`, `privacy`, `offline-first`, `sqlite`, `llm`
- [ ] GitHub repo has homepage URL set (landing page or PyPI)
- [ ] At least 2 issues labeled `good first issue`
- [ ] LICENSE file present and correct (MIT)
- [ ] CI is green on `main` branch

## Pre-launch: Content

- [ ] r/LocalLLaMA post reviewed and edited (`docs/launch/reddit_local_llama.md`)
- [ ] r/selfhosted post reviewed and edited (`docs/launch/reddit_selfhosted.md`)
- [ ] Show HN post reviewed and edited (`docs/launch/hackernews_show_hn.md`)
- [ ] Technical paper PDF exists at `docs/paper/zana_paper.pdf`
- [ ] A demo GIF or screenshot of `zana chat` in offline mode (optional but high-impact)

## Launch order (same day, 30 min apart)

1. **Show HN** — post at 7:30 AM EST Tuesday/Wednesday/Thursday
   - Immediately post first comment with technical details
   - Monitor and respond to every comment for first 2 hours

2. **r/LocalLLaMA** — post at 8:00 AM EST (same day)
   - Respond to all comments, especially "how does it compare to X"
   - Expected comparison: vs Ollama+WebUI, vs MemGPT, vs Open-Interpreter

3. **r/selfhosted** — post at 8:30 AM EST (same day)
   - Audience cares most about: no telemetry, portable files, Docker optional

## Post-launch: Monitoring

- [ ] Check PyPI download stats 24h after launch
- [ ] Check GitHub star count and new Issues
- [ ] Respond to all Issues opened within 24h
- [ ] If a question appears 3+ times → add to FAQ in README
- [ ] Check if anyone opened a PR — respond within 24h

## Amplification (day 2+)

- [ ] Cross-post to r/artificial (more philosophical angle, less technical)
- [ ] Cross-post to r/MachineLearning if paper gets traction
- [ ] Share on LinkedIn (personal brand — johntapias.com audience)
- [ ] Tweet/X thread with the architecture diagram
- [ ] Submit to: awesome-selfhosted list, awesome-local-llm list
- [ ] Submit to Lobsters (lobste.rs) — technical audience, appreciates depth

---

## What to prepare for (common objections)

| Objection | Response |
|---|---|
| "Just use MemGPT" | MemGPT is cloud-first, no Rust armor, no Civic Ledger, no offline tier |
| "Just use Ollama + Continue" | No persistent memory across sessions, no PII guard, no Mastery Map |
| "Why Python + Rust?" | Python for ergonomics (CLI, orchestration), Rust for the latency-critical paths (PII at 2.1µs, EML) |
| "What's the Civic Ledger for?" | Cryptographic audit of reasoning — if the AI made a decision, you can prove why |
| "Does it work on Windows?" | WSL yes, native PowerShell experimental — Windows native is on the roadmap |
| "Is it production ready?" | SPROUT tier (no Docker) is battle-tested. Full stack needs more hardening. |
