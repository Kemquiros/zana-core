#!/usr/bin/env bash
# 🧠 ZANA Installer v2.7.0 — Sovereign Cognitive Architecture
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

    if ! command -v git &>/dev/null; then
        echo -e "${RED}✗ Falta 'git'. Vital para descargar el Córtex.${RESET}"
        exit 1
    fi
    
    if ! command -v docker &>/dev/null; then
        echo -e "${YELLOW}⚠ Docker no detectado. Requerido para la Memoria Episódica y World Model.${RESET}"
        echo -e "${CYAN}ℹ Instala Docker desde https://docs.docker.com/get-docker/${RESET}"
        exit 1
    fi
}

install_core() {
    echo -e "${CYAN}▶ Forjando herramientas CLI...${RESET}"
    ZANA_REPO_DIR="$HOME/.zana/core-repo"
    
    # Use local path if developing, or clone repo otherwise.
    if [ -d "cli" ] && [ -d "sensory" ]; then
        echo -e "${CYAN}▶ Instalando desde entorno local de desarrollo...${RESET}"
        ZANA_REPO_DIR="$(pwd)"
        uv tool install "./cli" --force --quiet
    else
        echo -e "${CYAN}▶ Clonando repositorio maestro en $ZANA_REPO_DIR...${RESET}"
        mkdir -p "$HOME/.zana"
        if [ ! -d "$ZANA_REPO_DIR" ]; then
            git clone "https://github.com/$REPO.git" "$ZANA_REPO_DIR" --quiet
        else
            (cd "$ZANA_REPO_DIR" && git pull --quiet)
        fi
        uv tool install "$ZANA_REPO_DIR/cli" --force --quiet
    fi
    export ZANA_CORE_DIR="$ZANA_REPO_DIR"
}

configure_path() {
    mkdir -p "$ZANA_INSTALL_DIR"
    local shell_rc=""
    case "$SHELL" in
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        *)      shell_rc="$HOME/.bashrc" ;;
    esac

    # Ensure binary is in PATH
    if ! echo "$PATH" | grep -q "$ZANA_INSTALL_DIR"; then
        echo "export PATH=\"$ZANA_INSTALL_DIR:\$PATH\"" >> "$shell_rc"
        export PATH="$ZANA_INSTALL_DIR:$PATH"
        echo -e "${GREEN}✓ Binarios grabados en el PATH.${RESET}"
    fi

    # Inject ZANA_CORE_DIR for the CLI to find its stack
    if ! grep -q "ZANA_CORE_DIR" "$shell_rc"; then
        echo "export ZANA_CORE_DIR=\"$ZANA_CORE_DIR\"" >> "$shell_rc"
        echo -e "${GREEN}✓ Variable de entorno ZANA_CORE_DIR configurada.${RESET}"
    fi
}

# --- MAIN ---
banner
check_dependencies
install_core
configure_path

echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ZANA v2.7.0 — INSTALADA CON ÉXITO.${RESET}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "\n  ${MAGENTA}TU SOBERANÍA COGNITIVA HA DESPERTADO.${RESET}\n"

echo -e "${CYAN}▶ Iniciando protocolo de configuración automatizado (zana start)...${RESET}"
sleep 1
# Execute the newly installed binary to start the stack
"$ZANA_INSTALL_DIR/zana" start
