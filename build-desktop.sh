#!/usr/bin/env bash
# Build XANA Nodo Maestro — native desktop binaries (Linux .deb + .AppImage)
set -euo pipefail

BOLD='\033[1m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; RESET='\033[0m'

echo -e "${BOLD}[ XANA NODO MAESTRO — BUILD ]${RESET}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
UI="$ROOT/aria-ui"

# 1. Copy Rust .so sidecars into bundle resources
echo -e "${CYAN}▶ Copiando binarios Rust...${RESET}"
mkdir -p "$UI/src-tauri/sidecar"
cp "$ROOT/xana_steel_core.so" "$UI/src-tauri/resources/" 2>/dev/null || true
cp "$ROOT/xana_audio_dsp.so"  "$UI/src-tauri/resources/" 2>/dev/null || true

# 2. Package the Python gateway as frozen binary (PyInstaller)
if command -v pyinstaller &>/dev/null; then
  echo -e "${CYAN}▶ Empaquetando gateway con PyInstaller...${RESET}"
  cd "$ROOT/sensory"
  pyinstaller --onefile --name xana-gateway \
    --add-data "../xana_steel_core.so:." \
    --add-data "../xana_audio_dsp.so:."  \
    multimodal_gateway.py
  cp dist/xana-gateway "$UI/src-tauri/sidecar/xana-gateway-x86_64-unknown-linux-gnu"
  cd "$ROOT"
fi

# 3. Build Tauri desktop app
echo -e "${CYAN}▶ Compilando Nodo Maestro...${RESET}"
cd "$UI"
npm run tauri:build

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  BINARIOS EN: src-tauri/target/release/bundle/${RESET}"
ls src-tauri/target/release/bundle/ 2>/dev/null || true
