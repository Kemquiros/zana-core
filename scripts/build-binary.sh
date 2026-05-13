#!/usr/bin/env bash
set -euo pipefail

# colores
MAGENTA='\033[35m'; GREEN='\033[32m'; RESET='\033[0m'
info() { printf "${MAGENTA}[build]${RESET} %s\n" "$*"; }
ok()   { printf "${GREEN}[OK]${RESET}    %s\n" "$*"; }

# detectar OS y nombre del artefacto
case "$(uname -s)" in
  Linux*)  ARTIFACT="zana-linux-x86_64" ;;
  Darwin*) ARTIFACT="zana-macos-$(uname -m)" ;;
  *)       echo "OS no soportado"; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

info "Instalando dependencias de build..."
pip install pyinstaller --quiet
pip install -e "$REPO_ROOT/cli" --quiet

info "Compilando $ARTIFACT con PyInstaller..."
ZANA_MAIN=$(python3 -c "import zana.main; print(zana.main.__file__)")

pyinstaller \
  --onefile \
  --name zana \
  --strip \
  --clean \
  "$ZANA_MAIN" \
  --hidden-import zana \
  --hidden-import zana.commands \
  --collect-all zana \
  --exclude-module tkinter \
  --exclude-module matplotlib \
  --exclude-module numpy \
  --exclude-module PIL \
  -y

mv dist/zana "dist/$ARTIFACT"
chmod +x "dist/$ARTIFACT"

SIZE=$(du -sh "dist/$ARTIFACT" | cut -f1)
ok "Binario generado: dist/$ARTIFACT ($SIZE)"
ok "Pruébalo: ./dist/$ARTIFACT --version"
