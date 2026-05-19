#!/usr/bin/env bash
# sync-release.sh — ZANA multi-channel release synchronization
#
# Usage:
#   bash scripts/sync-release.sh <version>            # full sync
#   bash scripts/sync-release.sh <version> --dry-run  # preview only
#   bash scripts/sync-release.sh <version> --no-push  # local only (no git push)
#
# What it does:
#   1. Bumps version in cli/pyproject.toml
#   2. Bumps version in packages/zana-npm/package.json
#   3. Updates version badge in zana-landing (Navbar + capabilities page)
#   4. Commits and tags zana-core
#   5. Pushes tag → triggers CI/CD pipeline (GitHub Release + PyPI + npm)
#   6. Commits and pushes zana-landing separately
#
# What it does NOT do (CI/CD handles these):
#   - PyPI publish  (triggered by tag push in ci.yml)
#   - npm publish   (triggered by tag push in ci.yml)
#   - GitHub Release (triggered by tag push in ci.yml)
#   - Binary builds  (triggered by tag push in release-binaries.yml)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LANDING_ROOT="/home/kemquiros/Documentos/Personal/proyectos/XANA/zana-landing"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*" >&2; }
step() { echo -e "\n${CYAN}▶${NC}  $*"; }

# ── Args ──────────────────────────────────────────────────────────────────────
if [[ $# -lt 1 || "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: bash scripts/sync-release.sh <version> [--dry-run] [--no-push]"
    echo "Example: bash scripts/sync-release.sh 3.4.0"
    exit 0
fi

VERSION="$1"
DRY_RUN=false
NO_PUSH=false

for arg in "${@:2}"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --no-push) NO_PUSH=true ;;
    esac
done

# Validate semver format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]]; then
    err "Invalid version format: '$VERSION'. Expected: X.Y.Z or X.Y.Z-alpha.N"
    exit 1
fi

TAG="v${VERSION}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ZANA sync-release — ${TAG}"
[[ "$DRY_RUN" == "true" ]] && echo "  MODE: DRY RUN (no files written, no git ops)"
[[ "$NO_PUSH" == "true" ]] && echo "  MODE: NO PUSH (local commits only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Guard: check for uncommitted changes ──────────────────────────────────────
cd "$REPO_ROOT"
if [[ -n "$(git status --porcelain)" && "$DRY_RUN" == "false" ]]; then
    err "Working tree has uncommitted changes. Commit or stash first."
    git status --short
    exit 1
fi

# ── 1. CLI pyproject.toml ─────────────────────────────────────────────────────
step "Bumping cli/pyproject.toml → ${VERSION}"
CLI_TOML="$REPO_ROOT/cli/pyproject.toml"
CURRENT_CLI=$(grep '^version' "$CLI_TOML" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+[^"]*')

if [[ "$CURRENT_CLI" == "$VERSION" ]]; then
    warn "cli/pyproject.toml already at ${VERSION} — skipping"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        sed -i "s/^version = .*/version = \"${VERSION}\"/" "$CLI_TOML"
    fi
    ok "cli/pyproject.toml: ${CURRENT_CLI} → ${VERSION}"
fi

# ── 2. npm package.json ───────────────────────────────────────────────────────
step "Bumping packages/zana-npm/package.json → ${VERSION}"
NPM_PKG="$REPO_ROOT/packages/zana-npm/package.json"
CURRENT_NPM=$(grep '"version"' "$NPM_PKG" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+[^"]*')

if [[ "$CURRENT_NPM" == "$VERSION" ]]; then
    warn "package.json already at ${VERSION} — skipping"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" "$NPM_PKG"
    fi
    ok "packages/zana-npm/package.json: ${CURRENT_NPM} → ${VERSION}"
fi

# ── 3. CHANGELOG guard ────────────────────────────────────────────────────────
step "Checking CHANGELOG.md for ${VERSION} entry"
if grep -q "## \[${VERSION}\]" "$REPO_ROOT/CHANGELOG.md"; then
    ok "CHANGELOG.md has entry for ${VERSION}"
else
    warn "No CHANGELOG entry for ${VERSION}. Add one before releasing."
    warn "Template:"
    echo ""
    echo "  ## [${VERSION}] — $(date +%Y-%m-%d)"
    echo ""
    echo "  ### Added"
    echo "  - ..."
    echo ""
    if [[ "$DRY_RUN" == "false" ]]; then
        read -r -p "  Continue anyway? [y/N] " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
    fi
fi

# ── 4. Commit zana-core ───────────────────────────────────────────────────────
step "Committing zana-core changes"
if [[ "$DRY_RUN" == "false" ]]; then
    git add cli/pyproject.toml packages/zana-npm/package.json
    if git diff --cached --quiet; then
        warn "Nothing new to commit in zana-core"
    else
        git commit -m "chore: bump version to ${VERSION}

Co-Authored-By: sync-release.sh <noreply@vecanova.com>"
        ok "Committed: chore: bump version to ${VERSION}"
    fi
else
    ok "[dry-run] Would commit: chore: bump version to ${VERSION}"
fi

# ── 5. Tag ───────────────────────────────────────────────────────────────────
step "Tagging ${TAG}"
if git tag -l | grep -q "^${TAG}$"; then
    warn "Tag ${TAG} already exists — skipping tag creation"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        git tag -a "$TAG" -m "ZANA ${TAG}"
        ok "Created annotated tag ${TAG}"
    else
        ok "[dry-run] Would create tag: ${TAG}"
    fi
fi

# ── 6. Push zana-core + tag ───────────────────────────────────────────────────
step "Pushing zana-core"
if [[ "$DRY_RUN" == "false" && "$NO_PUSH" == "false" ]]; then
    git push origin HEAD
    git push origin "$TAG"
    ok "Pushed main + ${TAG} → CI/CD pipeline triggered"
    echo ""
    echo "  Pipeline: https://github.com/Kemquiros/zana-core/actions"
    echo "  Release:  https://github.com/Kemquiros/zana-core/releases/tag/${TAG}"
elif [[ "$NO_PUSH" == "true" ]]; then
    warn "--no-push: skipping git push. Run: git push origin HEAD && git push origin ${TAG}"
else
    ok "[dry-run] Would push: git push origin HEAD && git push origin ${TAG}"
fi

# ── 7. Update zana-landing ────────────────────────────────────────────────────
step "Updating zana-landing version references"

if [[ ! -d "$LANDING_ROOT" ]]; then
    warn "zana-landing not found at ${LANDING_ROOT} — skipping landing update"
else
    NAVBAR="$LANDING_ROOT/src/components/Navbar.tsx"
    CAPABILITIES="$LANDING_ROOT/src/app/[locale]/capabilities/page.tsx"

    update_file() {
        local file="$1"
        local pattern="$2"
        local replacement="$3"
        local label="$4"

        if [[ ! -f "$file" ]]; then
            warn "File not found: $file"
            return
        fi

        local current
        current=$(grep -oP "$pattern" "$file" | head -1 || true)

        if [[ -z "$current" ]]; then
            warn "Pattern not found in $label"
            return
        fi

        if [[ "$DRY_RUN" == "false" ]]; then
            sed -i "s/${current}/${replacement}/g" "$file"
        fi
        ok "${label}: ${current} → ${replacement}"
    }

    # Navbar: v3.X.Y
    update_file "$NAVBAR" \
        "v[0-9]+\.[0-9]+\.[0-9]+" \
        "v${VERSION}" \
        "Navbar.tsx"

    # Capabilities page: ZANA v3.X.Y
    update_file "$CAPABILITIES" \
        "v[0-9]+\.[0-9]+\.[0-9]+" \
        "v${VERSION}" \
        "capabilities/page.tsx"

    # Commit landing
    step "Committing zana-landing"
    cd "$LANDING_ROOT"
    if [[ "$DRY_RUN" == "false" ]]; then
        git add src/components/Navbar.tsx "src/app/[locale]/capabilities/page.tsx"
        if git diff --cached --quiet; then
            warn "Nothing to commit in zana-landing (already at ${VERSION}?)"
        else
            git commit -m "chore: bump ZANA version badge to ${VERSION}"
            ok "Committed zana-landing: bump version to ${VERSION}"
        fi
    else
        ok "[dry-run] Would commit zana-landing version bump"
    fi

    # Push landing
    if [[ "$DRY_RUN" == "false" && "$NO_PUSH" == "false" ]]; then
        git push origin HEAD
        ok "Pushed zana-landing"
    elif [[ "$NO_PUSH" == "true" ]]; then
        warn "--no-push: run 'git push origin HEAD' in zana-landing manually"
    fi

    cd "$REPO_ROOT"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ZANA ${TAG} — sync complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Channels updated:"
echo "    ✓  cli/pyproject.toml      → ${VERSION}"
echo "    ✓  packages/zana-npm       → ${VERSION}"
echo "    ✓  zana-landing Navbar     → v${VERSION}"
echo "    ✓  zana-landing capabilities → v${VERSION}"
echo ""
if [[ "$NO_PUSH" == "false" && "$DRY_RUN" == "false" ]]; then
    echo "  CI/CD pipeline triggered by tag ${TAG}:"
    echo "    → GitHub Release (CHANGELOG section extracted automatically)"
    echo "    → PyPI (vecanova-zana == ${VERSION})"
    echo "    → npm  (@vecanova/zana == ${VERSION})"
    echo "    → Binaries: Linux + Windows + macOS (release-binaries.yml)"
    echo ""
    echo "  Track progress:"
    echo "    https://github.com/Kemquiros/zana-core/actions"
fi
echo ""
