#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  ZANA Unified Release Pipeline v3.0
#  Publishes: PyPI · npm · GitHub Release  (in that order)
#
#  Usage:
#    ./publish-release.sh                    # publish current version
#    ./publish-release.sh --dry-run          # validate, skip all uploads
#    ./publish-release.sh --skip-pypi        # skip PyPI step
#    ./publish-release.sh --skip-npm         # skip npm step
#    ./publish-release.sh --skip-github      # skip GitHub release
#
#  Prerequisites:
#    pip install build twine hatchling
#    npm login  (logged in to npmjs.com)
#    gh auth login
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BOLD='\033[1m'; RESET='\033[0m'
GREEN='\033[0;32m'; CYAN='\033[0;36m'
RED='\033[0;31m'; YELLOW='\033[0;33m'
MAGENTA='\033[0;35m'

info()    { echo -e "${CYAN}  ▶ $*${RESET}"; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠ $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }
header()  { echo -e "\n${BOLD}${MAGENTA}$*${RESET}\n"; }

# ── Flags ──────────────────────────────────────────────────────────────────────
DRY_RUN=false; SKIP_PYPI=false; SKIP_NPM=false; SKIP_GITHUB=false
for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY_RUN=true ;;
    --skip-pypi)   SKIP_PYPI=true ;;
    --skip-npm)    SKIP_NPM=true ;;
    --skip-github) SKIP_GITHUB=true ;;
    *) error "Unknown flag: $arg" ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$REPO_ROOT/cli"
NPM_DIR="$REPO_ROOT/packages/zana-npm"

# ── Read canonical version from CLI pyproject.toml ─────────────────────────────
VERSION=$(python3 -c "
import tomllib
with open('$CLI_DIR/pyproject.toml', 'rb') as f:
    d = tomllib.load(f)
print(d['project']['version'])
")
TAG="v$VERSION"

# ── Banner ─────────────────────────────────────────────────────────────────────
echo -e "${BOLD}${MAGENTA}"
cat << 'EOF'
   ▲  ZANA RELEASE PIPELINE
  ███  PyPI · npm · GitHub
EOF
echo -e "${RESET}"
echo -e "  Version : ${BOLD}$VERSION${RESET}"
echo -e "  Tag     : ${BOLD}$TAG${RESET}"
echo -e "  Dry run : ${BOLD}$DRY_RUN${RESET}"
echo

# ── Pre-flight checks ──────────────────────────────────────────────────────────
header "[ 0 / 4 ] Pre-flight"

command -v python3   >/dev/null || error "python3 not found"
command -v git       >/dev/null || error "git not found"

if ! $SKIP_PYPI; then
  python3 -m twine --version >/dev/null 2>&1 || error "twine not found. Run: pip install build twine"
  python3 -m build --version >/dev/null 2>&1 || error "build not found. Run: pip install build"
fi
if ! $SKIP_NPM; then
  command -v npm >/dev/null || error "npm not found"
  npm whoami >/dev/null 2>&1 || error "Not logged in to npm. Run: npm login"
fi
if ! $SKIP_GITHUB; then
  command -v gh >/dev/null || error "gh CLI not found"
  gh auth status >/dev/null 2>&1 || error "Not authenticated to GitHub. Run: gh auth login"
fi

# Ensure working tree is clean
if ! git diff --quiet HEAD; then
  error "Working tree has uncommitted changes. Commit or stash before releasing."
fi

# Ensure tag doesn't already exist
if git tag | grep -q "^$TAG$"; then
  warn "Tag $TAG already exists locally. Proceeding anyway."
fi

success "Pre-flight OK — releasing $VERSION"

# ── Step 1: PyPI ───────────────────────────────────────────────────────────────
header "[ 1 / 4 ] PyPI — pip install zana"

if $SKIP_PYPI; then
  warn "PyPI step skipped (--skip-pypi)"
else
  info "Building wheel + sdist from $CLI_DIR ..."
  cd "$CLI_DIR"
  rm -rf dist/
  if $DRY_RUN; then
    info "[DRY RUN] python -m build"
  else
    python3 -m build
    info "Uploading to PyPI via twine ..."
    python3 -m twine upload dist/* --non-interactive
    success "PyPI upload complete — https://pypi.org/project/zana/$VERSION/"
  fi
  cd "$REPO_ROOT"
fi

# ── Step 2: npm ────────────────────────────────────────────────────────────────
header "[ 2 / 4 ] npm — npm install -g @vecanova/zana"

if $SKIP_NPM; then
  warn "npm step skipped (--skip-npm)"
else
  info "Syncing version in package.json to $VERSION ..."
  node -e "
    const fs = require('fs');
    const p = '$NPM_DIR/package.json';
    const pkg = JSON.parse(fs.readFileSync(p, 'utf8'));
    pkg.version = '$VERSION';
    fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + '\n');
    console.log('  package.json → ' + pkg.version);
  "
  if $DRY_RUN; then
    info "[DRY RUN] npm publish --access public"
  else
    cd "$NPM_DIR"
    npm publish --access public
    success "npm publish complete — https://www.npmjs.com/package/@vecanova/zana"
    cd "$REPO_ROOT"
    # Commit the version bump if package.json changed
    git add "$NPM_DIR/package.json"
    git diff --cached --quiet || git commit -m "chore: sync npm package.json to v$VERSION [skip ci]"
  fi
fi

# ── Step 3: Git tag ────────────────────────────────────────────────────────────
header "[ 3 / 4 ] Git tag"

if $DRY_RUN; then
  info "[DRY RUN] git tag $TAG && git push origin $TAG"
else
  git tag -a "$TAG" -m "ZANA $VERSION — Zero Friction Sovereign Architecture" 2>/dev/null || warn "Tag $TAG already exists, skipping"
  git push origin "$TAG" 2>/dev/null || warn "Tag push failed (may already exist on remote)"
  success "Tag $TAG pushed"
fi

# ── Step 4: GitHub Release ──────────────────────────────────────────────────────
header "[ 4 / 4 ] GitHub Release"

if $SKIP_GITHUB; then
  warn "GitHub release skipped (--skip-github)"
else
  RELEASE_NOTES="$(cat << NOTES
## ZANA $VERSION — Zero Friction Sovereign Architecture

Every person deserves their own Aeon. This release ships the complete v3.0 stack.

### What's new in v3.0

**Sentinel Event Bus** — 8 lifecycle events with SHA-256 Civic Ledger:
\`PreToolUse · PostToolUse · SkillActivation · ZSyncRequest · ExternalAPI · MemoryWrite · CivicLedgerEntry · AeonEvolution\`

**Zero Friction Install** — no Docker required by default:
\`\`\`bash
# Option A — curl
curl -LsSf https://zana.vecanova.com/install.sh | bash

# Option B — pip
pip install zana && zana init

# Option C — npm
npm install -g @vecanova/zana
\`\`\`

**Background Scheduler** — auto-mines trajectories into WisdomRules every 24h.

**Z-Skill v1.0** — SKILL.md format compatible with agentskills.io.

**SQLite episodic backend** — zero-config, stores at \`~/.zana/episodic.db\`.

**Herald Telegram Gateway** — circuit breaker, retry, rate limiting, webhook mode.

### Architecture
- Aeon (identity, memory, Civic Ledger) = LOCAL, sovereign, portable
- Model (inference) = swappable via \`ZANA_PRIMARY_MODEL\` env var
- Z-Protocol Stack: Z-Sovereign · Z-Identity · Z-Memory · Z-Think · Z-Skill · Z-Civic

---
*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*
NOTES
)"

  if $DRY_RUN; then
    info "[DRY RUN] gh release create $TAG"
    echo "$RELEASE_NOTES"
  else
    gh release create "$TAG" \
      --title "ZANA $VERSION — Zero Friction Sovereign Architecture" \
      --notes "$RELEASE_NOTES" \
      --repo "Kemquiros/zana-core"
    success "GitHub release created — https://github.com/Kemquiros/zana-core/releases/tag/$TAG"
  fi
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗"
echo "║   ZANA $VERSION RELEASED                        ║"
echo "║                                                  ║"
if ! $SKIP_PYPI && ! $DRY_RUN; then
echo "║   pip install zana==$VERSION                    ║"
fi
if ! $SKIP_NPM && ! $DRY_RUN; then
echo "║   npm install -g @vecanova/zana@$VERSION        ║"
fi
echo "║                                                  ║"
echo "║   Your data. Your hardware. Your soul.           ║"
echo -e "╚══════════════════════════════════════════════════╝${RESET}"
