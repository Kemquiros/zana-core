# Release Guide

How to cut and publish a XANA Core release on GitHub.

---

## Versioning

XANA follows [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH`
- **MAJOR**: breaking API changes
- **MINOR**: new features, backward-compatible
- **PATCH**: bug fixes

Current series: `1.x.x`

---

## Pre-release Checklist

- [ ] All tests pass locally
- [ ] Benchmark XFI ≥ 90 (hot mode with Docker)
- [ ] `CHANGELOG.md` updated with the new version section
- [ ] `.env.example` is current with all new variables
- [ ] No personal data in any source file
- [ ] No hardcoded API keys or secrets
- [ ] `README.md` reflects new capabilities

---

## Step-by-Step

### 1. Update CHANGELOG.md

Add a new section at the top:

```markdown
## [1.1.0] — 2026-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...
```

### 2. Commit the release

```bash
git add CHANGELOG.md README.md
git commit -m "chore: release v1.1.0"
```

### 3. Create and push the tag

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main
git push origin v1.1.0
```

### 4. Create GitHub Release

```bash
gh release create v1.1.0 \
  --title "XANA Core v1.1.0" \
  --notes-file <(cat CHANGELOG.md | head -30) \
  --latest
```

Or use the GitHub web UI: **Releases → Draft a new release → Choose tag v1.1.0**.

### 5. Attach build artifacts (optional)

If you want to distribute the pre-built Rust `.so`:

```bash
# Build
cd rust_core
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
cd ..

# Attach to release
gh release upload v1.1.0 xana_steel_core.so xana_armor.so
```

Note: compiled `.so` files are architecture-specific (x86-64 with AVX2). Users on different CPUs should build from source.

---

## Post-release

- [ ] Verify the release page looks correct on GitHub
- [ ] Update any linked documentation or changelogs
- [ ] Announce in project communication channels if applicable
