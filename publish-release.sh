#!/usr/bin/env bash
# 🚀 ZANA Release Tool — v2.6.4 Agnostic Release
set -euo pipefail

BOLD='\033[1m'
MAGENTA='\033[0;35m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}  ▶ $*${RESET}"; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }

VERSION="2.7.0"
TAG="v$VERSION"

echo -e "${BOLD}${MAGENTA}"
echo "  [ Z A N A   G I T H U B   R E L E A S E   (Agnostic) ]"
echo -e "${RESET}"

# 1. Crear Release en GitHub (Source only paradigm)
info "Creando release $TAG en GitHub..."
gh release create "$TAG" \
    --title "ZANA $VERSION — Soberanía Total" \
    --notes "### 🧠 ZANA Zero Autonomous Neural Architecture — v2.7.0 Sovereignty
    
Esta versión marca el inicio del paradigma **OS-Agnostic/Sovereign**. ZANA ya no se instala, ZANA habita tu hardware.

**Novedades Críticas:**
* **Sovereign Memory Engine v2 (Rust):** Motor vectorial nativo ultra-rápido reemplazando ChromaDB.
* **Ambient Senses (Voice DSP):** Escucha pasiva y detección de voz (VAD) en tiempo real vía Rust.
* **Hardened N8N Sandbox:** Orquestación y automatización segura integrada en Docker.
* **Aria UI (Web-First):** Interfaz sensorial optimizada para navegadores, eliminando fricción nativa.
* **Cross-Aeon Protocol:** Delegación agéntica formalizada para integraciones con KoruOS.

**Instalación Universal (Zero Friction):**
\`\`\`bash
curl -LsSf https://zana.vecanova.com/install.sh | bash
\`\`\`

---
*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*" \
    --repo "Kemquiros/zana-core"

success "¡Misión cumplida! El imperio cognitivo ha sido distribuido en GitHub."
echo -e "  Link: ${BOLD}https://github.com/Kemquiros/zana-core/releases/tag/$TAG${RESET}"
