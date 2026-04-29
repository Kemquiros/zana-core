#!/usr/bin/env bash
# 🧠 ZANA Installer v2.9.1 — Sovereign Cognitive Architecture
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

# --- LOCALIZATION ---
declare -A MSG_WELCOME MSG_DEP_CHECK MSG_DOCKER_MISSING MSG_PYTHON_MISSING MSG_UV_INSTALLING MSG_GIT_MISSING MSG_SUCCESS MSG_FORGING MSG_STARTING

# English
MSG_WELCOME[en]="ZANA IS ONLINE. Initializing Sovereign Protocol..."
MSG_DEP_CHECK[en]="Verifying system integrity..."
MSG_DOCKER_MISSING[en]="Docker not found. Needed for Sovereign Memory and local stores."
MSG_PYTHON_MISSING[en]="Python 3.12+ missing. It is the nervous system of logic."
MSG_GIT_MISSING[en]="Git not found. Needed to clone the Cortex."
MSG_UV_INSTALLING[en]="Installing 'uv' (Neural-speed Python manager)..."
MSG_SUCCESS[en]="ZANA v2.9.1 — INSTALLED SUCCESSFULLY."
MSG_FORGING[en]="Forging CLI tools..."
MSG_STARTING[en]="Starting automated configuration (zana start)..."

# Español
MSG_WELCOME[es]="ZANA EN LÍNEA. Inicializando Protocolo de Soberanía..."
MSG_DEP_CHECK[es]="Verificando integridad del sistema..."
MSG_DOCKER_MISSING[es]="Docker no detectado. Vital para la Memoria Soberana y almacenes locales."
MSG_PYTHON_MISSING[es]="Falta Python 3.12+. Es el sistema nervioso de la lógica."
MSG_GIT_MISSING[es]="Falta 'git'. Vital para clonar el Córtex."
MSG_UV_INSTALLING[es]="Instalando 'uv' (Gestor de Python de alta velocidad)..."
MSG_SUCCESS[es]="ZANA v2.9.1 — INSTALADA CON ÉXITO."
MSG_FORGING[es]="Forjando herramientas CLI..."
MSG_STARTING[es]="Iniciando protocolo de configuración automatizado (zana start)..."

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
    echo -e "${CYAN}▶ ${MSG_DEP_CHECK[$LANGUAGE]}${RESET}"
    
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}✗ ${MSG_PYTHON_MISSING[$LANGUAGE]}${RESET}"
        echo -e "${YELLOW}Install it from https://python.org${RESET}"
        exit 1
    fi

    if ! command -v git &>/dev/null; then
        echo -e "${RED}✗ ${MSG_GIT_MISSING[$LANGUAGE]}${RESET}"
        exit 1
    fi

    if ! command -v docker &>/dev/null; then
        echo -e "${YELLOW}⚠ ${MSG_DOCKER_MISSING[$LANGUAGE]}${RESET}"
        echo -e "${CYAN}ℹ Install Docker from https://docs.docker.com/get-docker/${RESET}"
        exit 1
    fi

    if ! command -v uv &>/dev/null; then
        echo -e "${CYAN}▶ ${MSG_UV_INSTALLING[$LANGUAGE]}${RESET}"
        curl -LsSf https://astral.sh/uv/install.sh | bash
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

install_core() {
    echo -e "${CYAN}▶ ${MSG_FORGING[$LANGUAGE]}${RESET}"
    ZANA_REPO_DIR="$HOME/.zana/core-repo"
    
    # Use local path if developing, or clone repo otherwise.
    if [ -d "cli" ] && [ -d "sensory" ]; then
        echo -e "${CYAN}▶ Installing from local development environment...${RESET}"
        ZANA_REPO_DIR="$(pwd)"
    else
        echo -e "${CYAN}▶ Cloning/Updating repository: $REPO...${RESET}"
        mkdir -p "$HOME/.zana"
        if [ ! -d "$ZANA_REPO_DIR" ]; then
            git clone "https://github.com/$REPO.git" "$ZANA_REPO_DIR"
        else
            (cd "$ZANA_REPO_DIR" && git fetch --all && git reset --hard origin/main)
        fi
    fi
    
    # Ensure fresh installation of the CLI tool
    echo -e "${CYAN}▶ Deploying ZANA CLI v2.9.1...${RESET}"
    uv tool uninstall zana || true
    uv tool install "$ZANA_REPO_DIR/cli" --force
    
    export ZANA_CORE_DIR="$ZANA_REPO_DIR"
}

configure_path() {
    mkdir -p "$ZANA_INSTALL_DIR"
    local shell_rc=""
    case "$SHELL" in
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        *)      shell_rc="$HOME/.bashrc" ;;
    esac

    # Path
    if ! echo "$PATH" | grep -q "$ZANA_INSTALL_DIR"; then
        echo "export PATH=\"$ZANA_INSTALL_DIR:\$PATH\"" >> "$shell_rc"
        export PATH="$ZANA_INSTALL_DIR:$PATH"
    fi

    # ZANA_CORE_DIR
    if ! grep -q "ZANA_CORE_DIR" "$shell_rc"; then
        echo "export ZANA_CORE_DIR=\"$ZANA_CORE_DIR\"" >> "$shell_rc"
    fi
}

# --- MAIN ---
banner
# Detect language
case "${LANG:-}" in
    es*) LANGUAGE="es" ;;
    *)   LANGUAGE="en" ;;
esac

echo -e "${CYAN}${MSG_WELCOME[$LANGUAGE]}${RESET}\n"

check_dependencies
install_core
configure_path

echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ${MSG_SUCCESS[$LANGUAGE]}${RESET}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "\n  ${MAGENTA}TU SOBERANÍA COGNITIVA HA DESPERTADO / YOUR COGNITIVE SOVEREIGNTY HAS AWAKENED.${RESET}\n"

echo -e "${CYAN}▶ ${MSG_STARTING[$LANGUAGE]}${RESET}"
sleep 1
"$ZANA_INSTALL_DIR/zana" start
