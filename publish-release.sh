#!/usr/bin/env bash
# 🚀 ZANA Release Tool — Distribución automática a GitHub
set -euo pipefail

BOLD='\033[1m'
MAGENTA='\033[0;35m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}  ▶ $*${RESET}"; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }

VERSION="2.6.1"
TAG="v$VERSION"
DEB_PATH="aria-ui/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/deb/ZANA_${VERSION}_amd64.deb"
APPIMAGE_PATH="aria-ui/src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/appimage/ZANA_${VERSION}_amd64.AppImage"

echo -e "${BOLD}${MAGENTA}"
echo "  [ Z A N A   G I T H U B   R E L E A S E ]"
echo -e "${RESET}"

# 1. Verificar archivos
if [ ! -f "$DEB_PATH" ]; then
    echo -e "  ⚠️  No se encontró el .deb en $DEB_PATH"
    exit 1
fi

# 2. Crear Release en GitHub
info "Creando release $TAG en GitHub..."
gh release create "$TAG" \
    --title "ZANA $VERSION — El Córtex ha despertado" \
    --notes "### 🧠 ZANA Zero Autonomous Neural Architecture
    
Esta versión incluye:
* **Protocolo de Instalación corregido** para Ubuntu.
* **Separación de procesos:** Instalación y ejecución ahora son manuales y soberanas.
* **Gateway Multimodal robusto:** Integración completa de tokenizers y lógica neuro-simbólica.
* **Aria UI:** Interfaz sensorial optimizada.

**Instalación en Ubuntu:**
\`\`\`bash
sudo dpkg -i ZANA_${VERSION}_amd64.deb
sudo apt install -f
\`\`\`" \
    --repo "Kemquiros/zana-core"

# 3. Subir Assets
info "Subiendo instalador .deb..."
gh release upload "$TAG" "$DEB_PATH" --repo "Kemquiros/zana-core"

if [ -f "$APPIMAGE_PATH" ]; then
    info "Subiendo instalador .AppImage..."
    gh release upload "$TAG" "$APPIMAGE_PATH" --repo "Kemquiros/zana-core"
fi

success "¡Misión cumplida! El imperio cognitivo ha sido distribuido en GitHub."
echo -e "  Link: ${BOLD}https://github.com/Kemquiros/zana-core/releases/tag/$TAG${RESET}"
