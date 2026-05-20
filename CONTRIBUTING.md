# Contributing to ZANA Core

> **No Docker required for most contributions.** The CLI, tests, and Rust core all build locally in under 2 minutes.

Thank you for your interest in contributing to ZANA — sovereign cognitive infrastructure for everyone.

---

## Quick Orientation

| Layer | Language | Where to look |
|---|---|---|
| CLI commands + ZSM | Python 3.12 | `cli/zana/commands/`, `cli/zana/core/` |
| Armor + Reasoning | Rust | `armor/`, `rust_core/` |
| Test suite | pytest | `cli/tests/` |
| Install scripts | bash / PowerShell | `scripts/` |
| Web UI | Next.js | `aria-ui/` |
| Full stack | Docker Compose | `docker-compose.yml` |

---

## Development Setup — No Docker

The fastest path to a working dev environment runs entirely without Docker:

```bash
git clone https://github.com/Kemquiros/zana-core.git
cd zana-core

# Install the CLI in editable mode (Python 3.12+ required)
pip install -e "cli/[dev]"

# Run the full test suite
pytest cli/tests/ -q
# Expected: 176 passed

# Verify linting
ruff check . && ruff format --check .
```

That's it. You're ready to work on any Python-layer feature.

### Running a specific test file

```bash
pytest cli/tests/test_skill.py -v
pytest cli/tests/test_sentinel_offline.py -v --tb=short
```

### Adding a new test

All tests use `tmp_path` + `monkeypatch` for full isolation. No shared state, no network, no Docker. Copy the pattern from any existing test in `cli/tests/`.

---

## Development Setup — Rust (optional)

Required only if you're touching `armor/` or `rust_core/`:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo build --release        # in armor/ or rust_core/
cargo fmt                    # before committing
cargo clippy -- -D warnings  # must be clean
```

---

## Development Setup — Full Stack (optional)

Only needed for gateway, ChromaDB, voice, or ARIA UI work:

```bash
cp .env.example .env         # fill in API keys if you have them
docker compose up -d         # starts PostgreSQL, ChromaDB, Neo4j, Redis, Caddy
zana start                   # boot the ZANA gateway
zana status                  # verify all services healthy
```

---

## Good First Issues

New here? These are the best places to start:

- Issues labeled [`good first issue`](https://github.com/Kemquiros/zana-core/issues?q=label%3A%22good+first+issue%22) — well-scoped, self-contained tasks
- Writing a new ZSM intent (`cli/zana/core/zsm.py`) — look at existing intents for the pattern
- Adding a new `zana skill` — create a `SKILL.md` in `~/.zana/skills/` and document the format
- Translating the `zana init` wizard to a new language
- Improving install guide docs in `docs/`

---

## Workflow

We follow a GitHub-native flow. Before writing code:

```bash
# 1. Check if an issue exists — open one if not
gh issue list --state open

# 2. Branch from develop
git checkout develop && git pull origin develop
git checkout -b feat/my-feature

# 3. Write code + tests
pytest cli/tests/ -q     # must be green
ruff check . --fix       # auto-fix lint
ruff format .

# 4. Push and open PR targeting develop
git push origin feat/my-feature
gh pr create --base develop --title "feat: my feature" --body "Closes #N"
```

**Never push directly to `main` or `develop`.** All changes go through a PR.

---

## Code Standards

| Rule | Why |
|---|---|
| English — all code, comments, docstrings, logs | Global contributor base |
| `ruff check .` must pass | CI blocks on lint errors |
| `pytest cli/tests/ -q` must pass | CI blocks on test failures |
| No hardcoded secrets | Use `.env` variables |
| No personal data in code | Use `tmp_path` in tests |
| `cargo fmt && cargo clippy -D warnings` for Rust | CI blocks on Rust warnings |

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add zana skill publish command
fix: handle WisdomQueue corrupt JSON on load
docs: add Spanish translation for zana init wizard
test: add coverage for SentinelLiteDB ring buffer pruning
chore: bump ruff to 0.9.0
refactor: extract _is_gateway_online() to shared util
```

---

## Pull Request Checklist

Before marking your PR ready for review:

- [ ] Branch is off `develop` (not `main`)
- [ ] Tests pass: `pytest cli/tests/ -q`
- [ ] Ruff clean: `ruff check . && ruff format --check .`
- [ ] PR title follows Conventional Commits
- [ ] PR body links the relevant issue (`Closes #N`)
- [ ] No secrets, personal data, or hardcoded URLs

---

## Reporting Bugs

Open an issue with:
- `pip show vecanova-zana` output (version)
- OS and Python version (`python --version`)
- Steps to reproduce
- Expected vs actual behavior
- Relevant output from `zana doctor`

---

## Security Issues

**Do not open a public issue for security vulnerabilities.**

Email the maintainers directly (see `pyproject.toml` → `[project.maintainers]`). We follow responsible disclosure and aim to respond within 48 hours.

---

## What We're Looking For

ZANA is MIT licensed. The Z-Protocol is free and open. We welcome:

| Contribution | Where |
|---|---|
| **New ZSM intents** | `cli/zana/core/zsm.py` |
| **New skills (SKILL.md)** | `cli/zana/skills/` |
| **Herald adapters** | `telegram_bot/` as reference |
| **Language translations** | `cli/zana/tui/onboarding.py` |
| **Model adapters** | LiteLLM-compatible — `router/` |
| **Rust contributions** | `armor/`, `rust_core/` |
| **Docs + guides** | `docs/` |
| **Bug reports** | GitHub Issues |

---

*ZANA is built in Medellín, Colombia. MIT License. VECANOVA.*
