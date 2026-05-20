#!/usr/bin/env bash
# sync-release.sh — ZANA multi-channel release synchronization
#
# Usage:
#   bash scripts/sync-release.sh <version>            # full sync (from develop or main)
#   bash scripts/sync-release.sh <version> --dry-run  # preview only
#   bash scripts/sync-release.sh <version> --no-push  # local commits, no git push
#   bash scripts/sync-release.sh <version> --hotfix   # skip develop→main branch dance
#
# Channels synced:
#   1. cli/pyproject.toml                (version bump)
#   2. packages/zana-npm/package.json    (version bump)
#   3. README.md                         (shield badge)
#   4. CHANGELOG.md                      (entry guard + template injection)
#   5. git tag vX.Y.Z                    (annotated)
#   6. GitHub Release + PyPI + npm       (CI/CD triggered by tag push)
#   7. zana-landing Navbar + capabilities (local script, NOT CI/CD)
#
# Branch flow (automatic):
#   develop → release/vX.Y.Z → main → tag → push
#   main    → version bump → tag → push  (use for hotfixes with --hotfix)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LANDING_ROOT="/home/kemquiros/Documentos/Personal/proyectos/XANA/zana-landing"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()    { echo -e "  ${GREEN}✓${NC}  $*"; }
warn()  { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "  ${RED}✗${NC}  $*" >&2; }
step()  { echo -e "\n${CYAN}▶${NC}  ${BOLD}$*${NC}"; }
info()  { echo -e "    ${CYAN}$*${NC}"; }

# ── Args ──────────────────────────────────────────────────────────────────────
if [[ $# -lt 1 || "$1" == "--help" || "$1" == "-h" ]]; then
    echo ""
    echo "  Usage: bash scripts/sync-release.sh <version> [flags]"
    echo ""
    echo "  Flags:"
    echo "    --dry-run   Preview all steps without writing files or pushing"
    echo "    --no-push   Apply local changes but skip git push / landing push"
    echo "    --hotfix    Skip develop→release/*→main branch dance (use from main)"
    echo ""
    echo "  Example:"
    echo "    bash scripts/sync-release.sh 3.5.0           # standard release from develop"
    echo "    bash scripts/sync-release.sh 3.5.1 --hotfix  # patch from main"
    echo "    bash scripts/sync-release.sh 3.5.0 --dry-run # preview"
    echo ""
    exit 0
fi

VERSION="$1"
DRY_RUN=false
NO_PUSH=false
HOTFIX=false

for arg in "${@:2}"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --no-push) NO_PUSH=true ;;
        --hotfix)  HOTFIX=true ;;
    esac
done

# Validate semver
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]]; then
    err "Invalid version: '$VERSION'. Expected X.Y.Z or X.Y.Z-alpha.N"
    exit 1
fi

TAG="v${VERSION}"
TODAY="$(date +%Y-%m-%d)"

echo ""
echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${BOLD}  ZANA sync-release — ${TAG}${NC}"
[[ "$DRY_RUN" == "true" ]] && echo "  MODE: DRY RUN (no files written, no git ops)"
[[ "$NO_PUSH"  == "true" ]] && echo "  MODE: NO PUSH (local commits only)"
[[ "$HOTFIX"   == "true" ]] && echo "  MODE: HOTFIX (branch dance skipped)"
echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$REPO_ROOT"

# ── Guard: uncommitted changes ────────────────────────────────────────────────
if [[ -n "$(git status --porcelain)" && "$DRY_RUN" == "false" ]]; then
    err "Working tree has uncommitted changes. Commit or stash first."
    git status --short
    exit 1
fi

# ── 0. Branch management ──────────────────────────────────────────────────────
CURRENT_BRANCH=$(git branch --show-current)
RELEASE_BRANCH="release/${TAG}"
MERGE_TO_MAIN=false

step "Branch setup"

if [[ "$HOTFIX" == "true" ]]; then
    if [[ "$CURRENT_BRANCH" != "main" ]]; then
        err "--hotfix requires being on main. Current branch: ${CURRENT_BRANCH}"
        exit 1
    fi
    ok "Hotfix mode — working directly on main"

elif [[ "$CURRENT_BRANCH" == "develop" ]]; then
    info "Starting from develop → will create ${RELEASE_BRANCH} → merge to main"
    if [[ "$DRY_RUN" == "false" ]]; then
        git pull origin develop
        git checkout -b "$RELEASE_BRANCH"
        ok "Created branch: ${RELEASE_BRANCH}"
    else
        ok "[dry-run] Would: git pull origin develop && git checkout -b ${RELEASE_BRANCH}"
    fi
    MERGE_TO_MAIN=true

elif [[ "$CURRENT_BRANCH" == release/* ]]; then
    info "Already on release branch: ${CURRENT_BRANCH}"
    MERGE_TO_MAIN=true

elif [[ "$CURRENT_BRANCH" == "main" ]]; then
    warn "On main without --hotfix. Continuing — PM confirmed this is intentional."

else
    err "Run from 'develop' or 'main'. Current branch: ${CURRENT_BRANCH}"
    err "To release from a feature branch, merge to develop first."
    exit 1
fi

# ── 1. cli/pyproject.toml ─────────────────────────────────────────────────────
step "Bumping cli/pyproject.toml → ${VERSION}"
CLI_TOML="$REPO_ROOT/cli/pyproject.toml"
CURRENT_CLI=$(grep '^version' "$CLI_TOML" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+[^"]*')

if [[ "$CURRENT_CLI" == "$VERSION" ]]; then
    warn "cli/pyproject.toml already at ${VERSION} — skipping"
else
    [[ "$DRY_RUN" == "false" ]] && sed -i "s/^version = .*/version = \"${VERSION}\"/" "$CLI_TOML"
    ok "cli/pyproject.toml: ${CURRENT_CLI} → ${VERSION}"
fi

# ── 2. packages/zana-npm/package.json ────────────────────────────────────────
step "Bumping packages/zana-npm/package.json → ${VERSION}"
NPM_PKG="$REPO_ROOT/packages/zana-npm/package.json"
CURRENT_NPM=$(grep '"version"' "$NPM_PKG" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+[^"]*')

if [[ "$CURRENT_NPM" == "$VERSION" ]]; then
    warn "package.json already at ${VERSION} — skipping"
else
    [[ "$DRY_RUN" == "false" ]] && sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" "$NPM_PKG"
    ok "packages/zana-npm/package.json: ${CURRENT_NPM} → ${VERSION}"
fi

# ── 3. README.md badge (root + cli/) ─────────────────────────────────────────
step "Updating README.md version badge → ${VERSION}"
README="$REPO_ROOT/README.md"
CLI_README="$REPO_ROOT/cli/README.md"
CURRENT_BADGE=$(grep -oP 'ZANA-v[0-9]+\.[0-9]+\.[0-9]+[^-]*' "$README" | head -1 || true)

if [[ -z "$CURRENT_BADGE" ]]; then
    warn "Version badge pattern not found in README.md — skipping"
elif [[ "$CURRENT_BADGE" == "ZANA-v${VERSION}" ]]; then
    warn "README.md badge already at v${VERSION} — skipping"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        sed -i "s|ZANA-v[0-9]\+\.[0-9]\+\.[0-9]\+[^-]*-10b981|ZANA-v${VERSION}-10b981|g" "$README"
    fi
    ok "README.md badge: ${CURRENT_BADGE} → ZANA-v${VERSION}"
fi

# cli/README.md feeds the PyPI long description — must stay in sync
CLI_BADGE=$(grep -oP 'ZANA-v[0-9]+\.[0-9]+\.[0-9]+[^-]*' "$CLI_README" | head -1 || true)
if [[ -z "$CLI_BADGE" ]]; then
    warn "Version badge pattern not found in cli/README.md — skipping"
elif [[ "$CLI_BADGE" == "ZANA-v${VERSION}" ]]; then
    warn "cli/README.md badge already at v${VERSION} — skipping"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        sed -i "s|ZANA-v[0-9]\+\.[0-9]\+\.[0-9]\+[^-]*-10b981|ZANA-v${VERSION}-10b981|g" "$CLI_README"
    fi
    ok "cli/README.md badge: ${CLI_BADGE} → ZANA-v${VERSION}"
fi

# ── 4. CHANGELOG.md ───────────────────────────────────────────────────────────
step "Checking CHANGELOG.md for [${VERSION}] entry"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"

if grep -q "## \[${VERSION}\]" "$CHANGELOG"; then
    ok "CHANGELOG.md already has entry for [${VERSION}]"
else
    warn "No CHANGELOG entry found for [${VERSION}]"
    echo ""
    echo "  Injecting template at the top of CHANGELOG.md..."
    TEMPLATE="## [${VERSION}] — ${TODAY}\n\n### Added\n- ...\n\n### Fixed\n- ...\n\n---\n\n"
    if [[ "$DRY_RUN" == "false" ]]; then
        # Insert template after the header block (after first ---)
        TMPFILE=$(mktemp)
        awk -v template="$TEMPLATE" '
            /^---$/ && !inserted {
                print; print ""; printf "%s", template; inserted=1; next
            }
            { print }
        ' "$CHANGELOG" > "$TMPFILE"
        mv "$TMPFILE" "$CHANGELOG"
        warn "Template injected — EDIT CHANGELOG.md before continuing."
        warn "Pausing 10 seconds. Open the file and update the entries."
        echo ""
        echo "  File: $CHANGELOG"
        echo ""
        sleep 10
    else
        ok "[dry-run] Would inject CHANGELOG template for [${VERSION}]"
    fi
fi

# ── 5. Commit ─────────────────────────────────────────────────────────────────
step "Committing version bump"
if [[ "$DRY_RUN" == "false" ]]; then
    git add cli/pyproject.toml packages/zana-npm/package.json README.md cli/README.md CHANGELOG.md
    if git diff --cached --quiet; then
        warn "Nothing new to commit (all files already at ${VERSION})"
    else
        git commit -m "chore: release ${TAG}

- cli/pyproject.toml → ${VERSION}
- packages/zana-npm/package.json → ${VERSION}
- README.md badge → v${VERSION}
- CHANGELOG.md entry for [${VERSION}]

Co-Authored-By: sync-release.sh <noreply@vecanova.com>"
        ok "Committed release bump for ${TAG}"
    fi
else
    ok "[dry-run] Would commit: chore: release ${TAG}"
fi

# ── 6. Merge release/* → main ─────────────────────────────────────────────────
if [[ "$MERGE_TO_MAIN" == "true" ]]; then
    step "Merging ${RELEASE_BRANCH} → main"
    if [[ "$DRY_RUN" == "false" && "$NO_PUSH" == "false" ]]; then
        # Push release branch first (preserves history, enables code review if needed)
        git push origin "$RELEASE_BRANCH"
        ok "Pushed ${RELEASE_BRANCH}"
        # Merge to main
        git checkout main
        git pull origin main
        git merge --no-ff "$RELEASE_BRANCH" -m "chore: merge ${RELEASE_BRANCH} into main"
        ok "Merged ${RELEASE_BRANCH} into main"
        # Clean up local release branch
        git branch -d "$RELEASE_BRANCH" 2>/dev/null || true
        ok "Deleted local branch ${RELEASE_BRANCH}"
    elif [[ "$NO_PUSH" == "true" ]]; then
        warn "--no-push: merge to main skipped. Run manually:"
        info "git push origin ${RELEASE_BRANCH}"
        info "git checkout main && git merge --no-ff ${RELEASE_BRANCH}"
    else
        ok "[dry-run] Would: push ${RELEASE_BRANCH} → merge to main → delete release branch"
    fi
fi

# ── 7. Tag ────────────────────────────────────────────────────────────────────
step "Tagging ${TAG} on main"
if git tag -l | grep -q "^${TAG}$"; then
    warn "Tag ${TAG} already exists — skipping"
else
    if [[ "$DRY_RUN" == "false" ]]; then
        git tag -a "$TAG" -m "ZANA ${TAG} — $(date +%Y-%m-%d)"
        ok "Annotated tag created: ${TAG}"
    else
        ok "[dry-run] Would: git tag -a ${TAG}"
    fi
fi

# ── 8. Push main + tag → CI/CD ────────────────────────────────────────────────
step "Pushing main + ${TAG}"
if [[ "$DRY_RUN" == "false" && "$NO_PUSH" == "false" ]]; then
    git push origin main
    git push origin "$TAG"
    ok "Pushed main + ${TAG} → CI/CD pipeline triggered"
    info ""
    info "Pipeline:  https://github.com/Kemquiros/zana-core/actions"
    info "Release:   https://github.com/Kemquiros/zana-core/releases/tag/${TAG}"
    info "PyPI:      https://pypi.org/project/vecanova-zana/${VERSION}/"
    info "npm:       https://www.npmjs.com/package/@vecanova/zana/v/${VERSION}"
elif [[ "$NO_PUSH" == "true" ]]; then
    warn "--no-push: run manually: git push origin main && git push origin ${TAG}"
else
    ok "[dry-run] Would: git push origin main && git push origin ${TAG}"
fi

# ── 9. zana-landing (NOT CI/CD — local script only) ──────────────────────────
step "Updating zana-landing (local, not CI/CD)"

if [[ ! -d "$LANDING_ROOT" ]]; then
    warn "zana-landing not found at ${LANDING_ROOT} — skipping"
else
    update_landing_file() {
        local file="$1" label="$2"
        if [[ ! -f "$file" ]]; then warn "Not found: $label"; return; fi
        local current; current=$(grep -oP "v[0-9]+\.[0-9]+\.[0-9]+" "$file" | head -1 || true)
        if [[ -z "$current" ]]; then warn "Version pattern not found in $label"; return; fi
        if [[ "$current" == "v${VERSION}" ]]; then warn "$label already at v${VERSION}"; return; fi
        [[ "$DRY_RUN" == "false" ]] && sed -i "s/${current}/v${VERSION}/g" "$file"
        ok "${label}: ${current} → v${VERSION}"
    }

    update_landing_file "$LANDING_ROOT/src/components/Navbar.tsx"                    "Navbar.tsx"
    update_landing_file "$LANDING_ROOT/src/app/[locale]/capabilities/page.tsx"       "capabilities/page.tsx"

    step "Committing + pushing zana-landing"
    cd "$LANDING_ROOT"
    if [[ "$DRY_RUN" == "false" ]]; then
        git add src/components/Navbar.tsx "src/app/[locale]/capabilities/page.tsx"
        if git diff --cached --quiet; then
            warn "zana-landing already at v${VERSION} — nothing to commit"
        else
            git commit -m "chore: bump ZANA version badge to v${VERSION}"
            ok "zana-landing committed"
        fi
        if [[ "$NO_PUSH" == "false" ]]; then
            git push origin HEAD
            ok "zana-landing pushed"
        else
            warn "--no-push: run 'git push origin HEAD' in zana-landing manually"
        fi
    else
        ok "[dry-run] Would commit + push zana-landing version bump"
    fi
    cd "$REPO_ROOT"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${BOLD}  ZANA ${TAG} — release complete${NC}"
echo "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Channels synced:"
echo "    ✓  cli/pyproject.toml              → ${VERSION}"
echo "    ✓  packages/zana-npm/package.json  → ${VERSION}"
echo "    ✓  README.md badge                 → v${VERSION}"
echo "    ✓  CHANGELOG.md                    → [${VERSION}] entry present"
echo "    ✓  zana-landing Navbar + capabilit → v${VERSION}"
echo ""
if [[ "$NO_PUSH" == "false" && "$DRY_RUN" == "false" ]]; then
    echo "  CI/CD triggered by tag ${TAG}:"
    echo "    → GitHub Release  (CHANGELOG section extracted automatically)"
    echo "    → PyPI            vecanova-zana==${VERSION}"
    echo "    → npm             @vecanova/zana@${VERSION}"
    echo "    → Binaries        Linux + Windows + macOS  (release-binaries.yml)"
    echo ""
    echo "  Track: https://github.com/Kemquiros/zana-core/actions"
fi
echo ""
