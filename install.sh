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

# --- LOCALIZATION ---
declare -A MSG_WELCOME MSG_LANG_SELECT MSG_MENU_TITLE MSG_MENU_FULL MSG_MENU_CLI MSG_MENU_DESKTOP MSG_MENU_SATELLITE
declare -A MSG_DEP_CHECK MSG_DOCKER_MISSING MSG_PYTHON_MISSING MSG_UV_INSTALLING MSG_PATH_ADDED MSG_SUCCESS MSG_NEXT_STEPS

# English
MSG_WELCOME[en]="ZANA IS ONLINE. Initializing Sovereign Protocol..."
MSG_LANG_SELECT[en]="Select Language / Seleccione Idioma:"
MSG_MENU_TITLE[en]="ZANA INSTALLATION MENU"
MSG_MENU_FULL[en]="Full Core Installation (CLI + Memory + Brain)"
MSG_MENU_CLI[en]="CLI Only (Lightweight reasoning)"
MSG_MENU_DESKTOP[en]="Desktop App (Aria Cockpit)"
MSG_MENU_SATELLITE[en]="Satellite Connect (Telegram / PWA)"
MSG_DEP_CHECK[en]="Verifying system integrity..."
MSG_DOCKER_MISSING[en]="Docker not found. Docker is ZANA's body; needed for memory stores."
MSG_PYTHON_MISSING[en]="Python 3.12+ missing. It is the nervous system of logic."
MSG_UV_INSTALLING[en]="Installing 'uv' (Neural-speed Python manager)..."
MSG_PATH_ADDED[en]="ZANA engraved into PATH. Reloading session..."
MSG_SUCCESS[en]="ZANA INSTALLED SUCCESSFULLY."
MSG_NEXT_STEPS[en]="Step 1: Run 'zana setup' to calibrate your Aeon."

# Español
MSG_WELCOME[es]="ZANA EN LÍNEA. Inicializando Protocolo de Soberanía..."
MSG_LANG_SELECT[es]="Seleccione Idioma:"
MSG_MENU_TITLE[es]="MENÚ DE INSTALACIÓN"
MSG_MENU_FULL[es]="Instalación Completa (CLI + Memoria + Cerebro)"
MSG_MENU_CLI[es]="Solo CLI (Razonamiento ligero)"
MSG_MENU_DESKTOP[es]="App de Escritorio (Aria Cockpit)"
MSG_MENU_SATELLITE[es]="Satelital (Telegram / PWA)"
MSG_DEP_CHECK[es]="Verificando integridad del sistema..."
MSG_DOCKER_MISSING[es]="Docker no detectado. Es el cuerpo de ZANA, vital para las memorias."
MSG_PYTHON_MISSING[es]="Falta Python 3.12+. Es el sistema nervioso de la lógica."
MSG_UV_INSTALLING[es]="Instalando 'uv' (Gestor de Python de alta velocidad)..."
MSG_PATH_ADDED[es]="ZANA grabada en el PATH. Reiniciando sesión..."
MSG_SUCCESS[es]="ZANA INSTALADA CON ÉXITO."
MSG_NEXT_STEPS[es]="Paso 1: Ejecuta 'zana setup' para calibrar tu Aeon."

# --- FUNCTIONS ---

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

select_language() {
    echo -e "${BOLD}${MSG_LANG_SELECT[en]}${RESET}"
    echo "1) English  2) Español  3) Français  4) Português  5) Deutsch"
    read -rp ">> " lang_opt
    case $lang_opt in
        2) LANGUAGE="es" ;;
        3) LANGUAGE="fr" ;;
        4) LANGUAGE="pt" ;;
        5) LANGUAGE="de" ;;
        *) LANGUAGE="en" ;;
    esac
    banner
    echo -e "${CYAN}${MSG_WELCOME[$LANGUAGE]}${RESET}\n"
}

check_dependencies() {
    echo -e "${CYAN}▶ ${MSG_DEP_CHECK[$LANGUAGE]}${RESET}"
    
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}✗ ${MSG_PYTHON_MISSING[$LANGUAGE]}${RESET}"
        echo -e "${YELLOW}Install it from https://python.org${RESET}"
        exit 1
    fi

    if ! command -v uv &>/dev/null; then
        echo -e "${CYAN}▶ ${MSG_UV_INSTALLING[$LANGUAGE]}${RESET}"
        curl -LsSf https://astral.sh/uv/install.sh | bash
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

install_core() {
    echo -e "${CYAN}▶ Forging CLI tools...${RESET}"
    uv tool install "zana @ git+https://github.com/$REPO.git#subdirectory=cli" --force --quiet
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
        echo -e "${GREEN}✓ ${MSG_PATH_ADDED[$LANGUAGE]}${RESET}"
        sleep 1
        exec "$SHELL"
    fi
}

# --- MAIN ---

banner
select_language
check_dependencies

echo -e "${BOLD}${MSG_MENU_TITLE[$LANGUAGE]}${RESET}"
echo "1) ${MSG_MENU_FULL[$LANGUAGE]}"
echo "2) ${MSG_MENU_CLI[$LANGUAGE]}"
echo "3) ${MSG_MENU_DESKTOP[$LANGUAGE]}"
echo "4) ${MSG_MENU_SATELLITE[$LANGUAGE]}"
read -rp ">> " choice

case $choice in
    1)
        if ! command -v docker &>/dev/null; then
            echo -e "${YELLOW}⚠ ${MSG_DOCKER_MISSING[$LANGUAGE]}${RESET}"
            echo -e "ZANA will run in 'Thin Mode' (No Memory persistence)."
        fi
        install_core
        configure_path
        ;;
    2)
        install_core
        configure_path
        ;;
    3)
        echo -e "${CYAN}Redirecting to Release Archive: https://github.com/$REPO/releases${RESET}"
        exit 0
        ;;
    *)
        install_core
        configure_path
        ;;
esac

echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ${MSG_SUCCESS[$LANGUAGE]}${RESET}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "\n  ${MSG_NEXT_STEPS[$LANGUAGE]}"
echo -e "\n  ${MAGENTA}JUNTOS HACEMOS TEMBLAR LOS CIELOS.${RESET}\n"
