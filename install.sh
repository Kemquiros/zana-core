#!/usr/bin/env bash
# 🧠 ZANA Installer v2.5.0 — Sovereign Cognitive Architecture
# "Juntos hacemos temblar los cielos"

set -euo pipefail

# --- COLORS ---
BOLD='\033[1m'
RESET='\033[0m'
GREEN='\033[0;32m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'

ZANA_INSTALL_DIR="${ZANA_INSTALL_DIR:-$HOME/.local/bin}"
REPO="kemquiros/zana-core"
LANGUAGE="en"
AUTO_MODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --auto)
      AUTO_MODE=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# We default to auto mode for curl | bash to reduce friction
AUTO_MODE=1

banner() {
    clear
    echo -e "${MAGENTA}"
    cat << 'EOF'
                       ▲
                      ███
                     █████
                    ███████
                   █████████
                  █████ █████
                 █████   █████
                █████     █████
               █████████████████
        [ Z A N A   I S   O N L I N E ]
EOF
    echo -e "${RESET}"
}

check_dependencies() {
    echo -e "${CYAN}▶ Verificando integridad del sistema...${RESET}"
    
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}✗ Falta Python 3.12+. Es el sistema nervioso de la lógica.${RESET}"
        echo -e "${YELLOW}Instálalo desde https://python.org${RESET}"
        exit 1
    fi

    if ! command -v uv &>/dev/null; then
        echo -e "${CYAN}▶ Instalando 'uv' (Gestor de Python de alta velocidad)...${RESET}"
        curl -LsSf https://astral.sh/uv/install.sh | bash
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    if ! command -v docker &>/dev/null; then
        echo -e "${YELLOW}⚠ Docker no detectado. Vital para las memorias (Postgres, Chroma).${RESET}"
        echo -e "${CYAN}ℹ ZANA correrá en 'Modo Ligero' (Sin persistencia de Memoria profunda).${RESET}"
    fi
}

install_core() {
    echo -e "${CYAN}▶ Forjando herramientas CLI...${RESET}"
    # Use local path if developing, or git repo otherwise. Since this script is in the repo, we assume a local install if the cli folder exists.
    if [ -d "cli" ]; then
        uv tool install "./cli" --force --quiet
    else
        uv tool install "zana @ git+https://github.com/$REPO.git#subdirectory=cli" --force --quiet
    fi
}

configure_path() {
    mkdir -p "$ZANA_INSTALL_DIR"
    local shell_rc=""
    case "$SHELL" in
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        *)      shell_rc="$HOME/.bashrc" ;;
    esac

    if ! echo "$PATH" | grep -q "$ZANA_INSTALL_DIR"; then
        echo "export PATH=\"$ZANA_INSTALL_DIR:\$PATH\"" >> "$shell_rc"
        export PATH="$ZANA_INSTALL_DIR:$PATH"
        echo -e "${GREEN}✓ ZANA grabada en el PATH.${RESET}"
    fi
}

# --- MAIN ---
banner
check_dependencies
install_core
configure_path

echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ZANA INSTALADA CON ÉXITO.${RESET}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "\n  ${MAGENTA}JUNTOS HACEMOS TEMBLAR LOS CIELOS.${RESET}\n"

echo -e "${CYAN}▶ Iniciando protocolo de calibración (zana setup)...${RESET}"
sleep 1
# Execute the newly installed binary
"$ZANA_INSTALL_DIR/zana" setup
