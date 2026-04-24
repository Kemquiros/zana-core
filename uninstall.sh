#!/usr/bin/env bash
# 🧠 ZANA Uninstaller — Sovereign Cognitive Architecture

set -euo pipefail

# --- COLORS ---
BOLD='\033[1m'
RESET='\033[0m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GREEN='\033[0;32m'

banner() {
    clear
    echo -e "${MAGENTA}"
    cat << 'EOF'
                       ▼
                      ███
                     █████
                    ███████
                   █████████
                  █████ █████
                 █████   █████
                █████     █████
               █████████████████
        [ P R O T O C O L O   O M E G A ]
EOF
    echo -e "${RESET}"
}

remove_system_package() {
    echo -e "${CYAN}▶ Buscando paquete ZANA en el sistema...${RESET}"
    if dpkg -l | grep -q "zana "; then
        echo -e "${YELLOW}Desinstalando aplicación de escritorio (zana-desktop)...${RESET}"
        sudo apt-get remove -y zana || true
        echo -e "${GREEN}✓ Aplicación de escritorio eliminada.${RESET}"
    else
        echo -e "${CYAN}ℹ No se encontró paquete .deb de escritorio instalado.${RESET}"
    fi
}

remove_cli_tools() {
    echo -e "${CYAN}▶ Limpiando herramientas CLI (uv)...${RESET}"
    if command -v uv &>/dev/null; then
        if uv tool list 2>/dev/null | grep -q "zana"; then
            uv tool uninstall zana --quiet || true
            echo -e "${GREEN}✓ CLI 'zana' eliminado.${RESET}"
        fi
    fi
    
    # Clean up environment variables in .bashrc or .zshrc
    echo -e "${CYAN}▶ Limpiando variables de entorno en perfiles de shell...${RESET}"
    local shell_rc=""
    case "$SHELL" in
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        *)      shell_rc="$HOME/.bashrc" ;;
    esac
    
    if [ -f "$shell_rc" ]; then
        if grep -q "ZANA_CORE_DIR" "$shell_rc"; then
            sed -i '/ZANA_CORE_DIR/d' "$shell_rc"
            echo -e "${GREEN}✓ Variables de ZANA removidas de $shell_rc${RESET}"
        fi
    fi
}

remove_user_data() {
    echo -e "${RED}▶ ADVERTENCIA: Eliminando bóveda de conocimientos y base de datos local...${RESET}"
    
    # Tauri / Desktop App SQLite Data
    local data_dir="$HOME/.local/share/ZANA"
    if [ -d "$data_dir" ]; then
        rm -rf "$data_dir"
        echo -e "${GREEN}✓ Bóveda SQLite de Tauri eliminada ($data_dir).${RESET}"
    fi
    
    # CLI Data
    local cli_dir="$HOME/.zana"
    if [ -d "$cli_dir" ]; then
        rm -rf "$cli_dir"
        echo -e "${GREEN}✓ Datos de CLI y repositorios cacheados eliminados ($cli_dir).${RESET}"
    fi
    
    echo -e "${GREEN}✓ Toda tu memoria y configuración ha sido erradicada.${RESET}"
}

# --- MAIN ---
banner
echo -e "${BOLD}Has invocado el protocolo de desinstalación de ZANA.${RESET}"
echo -e "Tienes dos opciones:\n"
echo -e "  [1] ${CYAN}Desinstalar aplicación${RESET} (Mantiene tus chats, configuraciones y base de datos intactos)."
echo -e "  [2] ${RED}Erradicación Total${RESET} (Borra la aplicación y DESTRUYE toda tu bóveda de datos y configuración).\n"

read -p "Selecciona una opción [1/2]: " option

case "$option" in
    1)
        echo -e "\n${CYAN}Iniciando desinstalación segura (Reteniendo memoria)...${RESET}"
        remove_system_package
        remove_cli_tools
        echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "${BOLD}  ZANA SE HA DESCONECTADO.${RESET}"
        echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "  Tus recuerdos están a salvo en el disco."
        ;;
    2)
        echo -e "\n${RED}Iniciando Protocolo Omega (Destrucción Total)...${RESET}"
        
        read -p "¿Estás ABSOLUTAMENTE seguro de borrar todos tus datos? Escribe 'ZANA' para confirmar: " confirm
        if [ "$confirm" != "ZANA" ]; then
            echo -e "${CYAN}Abortando erradicación de datos. ZANA sobrevive.${RESET}"
            exit 1
        fi
        
        remove_system_package
        remove_cli_tools
        remove_user_data
        
        echo -e "\n${BOLD}${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "${BOLD}  ZANA HA SIDO ERRADICADA.${RESET}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "  No quedan rastros cognitivos en este sistema."
        ;;
    *)
        echo -e "${YELLOW}Opción inválida. Abortando.${RESET}"
        exit 1
        ;;
esac

exit 0
