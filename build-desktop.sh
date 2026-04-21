#!/usr/bin/env bash
# ZANA Desktop Build — native binaries (.deb, .AppImage, .dmg, .msi)
# Usage: ./build-desktop.sh [--target <triple>]
set -euo pipefail

BOLD='\033[1m'
MAGENTA='\033[0;35m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

info()    { echo -e "${CYAN}  ▶ $*${RESET}"; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠ $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")" && pwd)"
UI="$ROOT/aria-ui"
RESOURCES="$UI/src-tauri/resources"
SIDECAR_DIR="$UI/src-tauri/sidecar"
TARGET="${1:-}"

echo -e "${BOLD}${MAGENTA}"
echo "  [ Z A N A   D E S K T O P   B U I L D ]"
echo -e "${RESET}"

# Detect target triple
if [ -z "$TARGET" ]; then
    ARCH="$(uname -m)"
    OS="$(uname -s)"
    case "$OS-$ARCH" in
        Linux-x86_64)  TARGET="x86_64-unknown-linux-gnu" ;;
        Linux-aarch64) TARGET="aarch64-unknown-linux-gnu" ;;
        Darwin-x86_64) TARGET="x86_64-apple-darwin" ;;
        Darwin-arm64)  TARGET="aarch64-apple-darwin" ;;
        *)             warn "Unknown platform $OS-$ARCH, using default target" ;;
    esac
fi
info "Target: ${TARGET:-native}"

# ── Step 1: Copy Rust .so sidecars into bundle resources ─────────────────────
info "Copying Rust binaries to resources..."
mkdir -p "$RESOURCES" "$SIDECAR_DIR"

for so in zana_steel_core.so zana_audio_dsp.so zana_armor.so; do
    if [ -f "$ROOT/$so" ]; then
        cp "$ROOT/$so" "$RESOURCES/$so"
        success "  $so"
    else
        warn "$so not found in $ROOT — skipping"
    fi
done

# ── Step 2: Package Python gateway as frozen sidecar binary ──────────────────
SIDECAR_BIN="$SIDECAR_DIR/zana-gateway${TARGET:+-$TARGET}"

if command -v pyinstaller &>/dev/null; then
    info "Packaging gateway with PyInstaller..."
    cd "$ROOT/sensory"

    pyinstaller \
        --onefile \
        --name zana-gateway \
        --add-data "../zana_steel_core.so:." \
        --add-data "../zana_audio_dsp.so:."  \
        --add-data "../zana_armor.so:."       \
        --hidden-import faster_whisper        \
        --hidden-import litellm               \
        multimodal_gateway.py

    cp "dist/zana-gateway" "$SIDECAR_BIN"
    chmod +x "$SIDECAR_BIN"
    success "Gateway binary → $SIDECAR_BIN"
    cd "$ROOT"
else
    warn "PyInstaller not found. Gateway sidecar will not be bundled."
    warn "Install with: pip install pyinstaller"
    warn "The app will launch but won't auto-start the gateway."

    # Ensure stub exists so Tauri build doesn't fail on externalBin declaration
    if [ ! -f "$SIDECAR_BIN" ]; then
        printf '#!/bin/sh\necho "zana-gateway: not built" >&2\nexit 1\n' > "$SIDECAR_BIN"
        chmod +x "$SIDECAR_BIN"
    fi
fi

# ── Step 3: Build Tauri desktop app ──────────────────────────────────────────
info "Building ZANA desktop app (Tauri)..."
cd "$UI"

BUILD_CMD="npm run tauri:build"
if [ -n "$TARGET" ]; then
    BUILD_CMD="npm run tauri:build -- --target $TARGET"
fi

eval "$BUILD_CMD"

# ── Summary ───────────────────────────────────────────────────────────────────
BUNDLE_DIR="$UI/src-tauri/target/${TARGET:+$TARGET/}release/bundle"
# Fallback path if target not specified
[ -d "$BUNDLE_DIR" ] || BUNDLE_DIR="$UI/src-tauri/target/release/bundle"

echo ""
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ZANA DESKTOP — BUILD COMPLETE${RESET}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

if [ -d "$BUNDLE_DIR" ]; then
    find "$BUNDLE_DIR" -name "*.deb" -o -name "*.AppImage" \
         -o -name "*.dmg" -o -name "*.msi" 2>/dev/null \
    | while read -r f; do
        SIZE=$(du -sh "$f" | cut -f1)
        echo -e "  ${GREEN}$(basename "$f")${RESET}  (${SIZE})"
        echo -e "  ${CYAN}$f${RESET}"
        echo ""
    done
else
    warn "Bundle dir not found at $BUNDLE_DIR"
fi

echo -e "  ${MAGENTA}JUNTOS HACEMOS TEMBLAR LOS CIELOS.${RESET}"
echo ""
