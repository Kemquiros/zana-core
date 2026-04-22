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
declare -A MSG_FORGING MSG_THIN_MODE

# English
MSG_WELCOME[en]="ZANA IS ONLINE. Initializing Sovereign Protocol..."
MSG_LANG_SELECT[en]="Select Language / Seleccione Idioma:"
MSG_MENU_TITLE[en]="ZANA INSTALLATION MENU"
MSG_MENU_FULL[en]="Full Core Installation (CLI + Memory + Brain)"
MSG_MENU_CLI[en]="CLI Only (Lightweight reasoning)"
MSG_MENU_DESKTOP[en]="Desktop App (Aria Cockpit)"
MSG_MENU_SATELLITE[en]="Satellite Connect (Telegram / PWA)"
MSG_DEP_CHECK[en]="Verifying system integrity..."
MSG_DOCKER_MISSING[en]="Docker not found. Needed for memory stores (Postgres, Chroma)."
MSG_PYTHON_MISSING[en]="Python 3.12+ missing. It is the nervous system of logic."
MSG_UV_INSTALLING[en]="Installing 'uv' (Neural-speed Python manager)..."
MSG_PATH_ADDED[en]="ZANA engraved into PATH. Reloading session..."
MSG_SUCCESS[en]="ZANA INSTALLED SUCCESSFULLY."
MSG_NEXT_STEPS[en]="Step 1: Run 'zana setup' to calibrate your Aeon."
MSG_FORGING[en]="Forging CLI tools..."
MSG_THIN_MODE[en]="ZANA will run in 'Thin Mode' (No Memory persistence)."

# Español
MSG_WELCOME[es]="ZANA EN LÍNEA. Inicializando Protocolo de Soberanía..."
MSG_LANG_SELECT[es]="Seleccione Idioma:"
MSG_MENU_TITLE[es]="MENÚ DE INSTALACIÓN"
MSG_MENU_FULL[es]="Instalación Completa (CLI + Memoria + Cerebro)"
MSG_MENU_CLI[es]="Solo CLI (Razonamiento ligero)"
MSG_MENU_DESKTOP[es]="App de Escritorio (Aria Cockpit)"
MSG_MENU_SATELLITE[es]="Satelital (Telegram / PWA)"
MSG_DEP_CHECK[es]="Verificando integridad del sistema..."
MSG_DOCKER_MISSING[es]="Docker no detectado. Vital para las memorias (Postgres, Chroma)."
MSG_PYTHON_MISSING[es]="Falta Python 3.12+. Es el sistema nervioso de la lógica."
MSG_UV_INSTALLING[es]="Instalando 'uv' (Gestor de Python de alta velocidad)..."
MSG_PATH_ADDED[es]="ZANA grabada en el PATH. Reiniciando sesión..."
MSG_SUCCESS[es]="ZANA INSTALADA CON ÉXITO."
MSG_NEXT_STEPS[es]="Paso 1: Ejecuta 'zana setup' para calibrar tu Aeon."
MSG_FORGING[es]="Forjando herramientas CLI..."
MSG_THIN_MODE[es]="ZANA correrá en 'Modo Ligero' (Sin persistencia de Memoria)."

# French
MSG_WELCOME[fr]="ZANA EST EN LIGNE. Initialisation du Protocole de Souveraineté..."
MSG_MENU_TITLE[fr]="MENU D'INSTALLATION"
MSG_MENU_FULL[fr]="Installation Complète (CLI + Mémoire + Cerveau)"
MSG_MENU_CLI[fr]="CLI uniquement (Raisonnement léger)"
MSG_MENU_DESKTOP[fr]="Application de bureau (Aria Cockpit)"
MSG_MENU_SATELLITE[fr]="Satellite (Telegram / PWA)"
MSG_SUCCESS[fr]="ZANA INSTALLÉE AVEC SUCCÈS."
MSG_NEXT_STEPS[fr]="Étape 1 : Exécutez 'zana setup' pour calibrer votre Aeon."
MSG_FORGING[fr]="Forgage des outils CLI..."

# Portuguese
MSG_WELCOME[pt]="ZANA ESTÁ ONLINE. Inicializando Protocolo de Soberania..."
MSG_MENU_TITLE[pt]="MENU DE INSTALAÇÃO"
MSG_MENU_FULL[pt]="Instalação Completa (CLI + Memória + Cérebro)"
MSG_MENU_CLI[pt]="Apenas CLI (Raciocínio leve)"
MSG_MENU_DESKTOP[pt]="App de Desktop (Aria Cockpit)"
MSG_MENU_SATELLITE[pt]="Satélite (Telegram / PWA)"
MSG_SUCCESS[pt]="ZANA INSTALADA COM SUCESSO."
MSG_NEXT_STEPS[pt]="Passo 1: Execute 'zana setup' para calibrar seu Aeon."
MSG_FORGING[pt]="Forjando ferramentas CLI..."

# German
MSG_WELCOME[de]="ZANA IST ONLINE. Souveränitätsprotokoll wird initialisiert..."
MSG_MENU_TITLE[de]="INSTALLATIONSMENÜ"
MSG_MENU_FULL[de]="Vollständige Installation (CLI + Speicher + Gehirn)"
MSG_MENU_CLI[de]="Nur CLI (Leichtgewichtige Logik)"
MSG_MENU_DESKTOP[de]="Desktop-App (Aria Cockpit)"
MSG_MENU_SATELLITE[de]="Satellit (Telegram / PWA)"
MSG_SUCCESS[de]="ZANA ERFOLGREICH INSTALLIERT."
MSG_NEXT_STEPS[de]="Schritt 1: Führen Sie 'zana setup' aus, um Ihren Aeon zu kalibrieren."
MSG_FORGING[de]="CLI-Tools werden geschmiedet..."

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
    echo -e "${CYAN}▶ ${MSG_FORGING[$LANGUAGE]}${RESET}"
    # Use direct repo URL to ensure we get the latest stable code
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
        export PATH="$ZANA_INSTALL_DIR:$PATH"
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
            echo -e "${CYAN}ℹ ${MSG_THIN_MODE[$LANGUAGE]}${RESET}"
        fi
        install_core
        configure_path
        ;;
    2)
        install_core
        configure_path
        ;;
    3)
        echo -e "${CYAN}Download Tauri binary from: https://github.com/$REPO/releases${RESET}"
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
