# Contributing to XANA Core

Thank you for your interest in contributing.

## Before You Start

- Check [open issues](../../issues) to avoid duplicating effort.
- For large changes, open an issue first to discuss the approach.
- All code and comments must be in English.

## Development Setup

```bash
git clone https://github.com/your-org/xana-core.git
cd xana-core
cp .env.example .env
docker compose up -d
cd sensory && uv sync
```

## Code Standards

- **Python**: follow existing style (no strict linter enforced yet)
- **Rust**: `cargo fmt` before committing
- **No personal data**: no real names, emails, or private URLs in code
- **No hardcoded secrets**: use `.env` variables
- **English only**: all comments, docstrings, log messages

## Pull Request Process

1. Fork the repo and create a feature branch: `git checkout -b feat/my-feature`
2. Write or update tests if relevant
3. Run the benchmark to verify no regression: `cd sensory && uv run python ../tests/benchmark_xana.py`
4. Open a PR with a clear title and description
5. Link the PR to the relevant issue if applicable

## Commit Messages

Use conventional commits:

```
feat: add streaming TTS endpoint
fix: correct Kalman buffer alignment on ARM
docs: update deployment guide for k8s
chore: bump rust edition to 2024
```

## Reporting Bugs

Open an issue with:
- XANA version / commit hash
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Security Issues

Do **not** open a public issue for security vulnerabilities. Email the maintainers directly (see `pyproject.toml`).
