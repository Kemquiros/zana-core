#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  ZANA Installer v3.0.0 — Sovereign Cognitive Architecture
#  "Juntos hacemos temblar los cielos"
#
#  Non-interactive / CI mode (set before running):
#    ZANA_NON_INTERACTIVE=1   — skip all prompts, use defaults
#    ZANA_LANG=es             — preset language (en|es|pt|fr|it|de)
#    ZANA_FULL_RESET=true     — wipe Aeon data before installing
#    ZANA_VAULT_PATH=/path    — set vault path without prompts
#    ZANA_INSTALL_DIR=/path   — override CLI install directory
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
RESET='\033[0m'
GREEN='\033[0;32m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
DIM='\033[2m'

ZANA_INSTALL_DIR="${ZANA_INSTALL_DIR:-$HOME/.local/bin}"
REPO="kemquiros/zana-core"
LANGUAGE="${ZANA_LANG:-en}"
ZANA_FULL_RESET="${ZANA_FULL_RESET:-false}"

# ── Localization ───────────────────────────────────────────────────────────────
declare -A MSG_WELCOME MSG_DEP_CHECK MSG_DOCKER_MISSING MSG_PYTHON_MISSING \
            MSG_UV_INSTALLING MSG_GIT_MISSING MSG_SUCCESS MSG_FORGING \
            MSG_STARTING MSG_MODE_PROMPT MSG_MODE_UPDATE MSG_MODE_FULL \
            MSG_MODE_CONFIRM MSG_DATA_WIPED MSG_SOVEREIGNTY MSG_LANG_PROMPT \
            MSG_RUST_INSTALLING MSG_RUST_OK

# ── English ───────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[en]="Select your language / Elige tu idioma:"
MSG_WELCOME[en]="ZANA IS ONLINE. Initializing Sovereign Protocol..."
MSG_DEP_CHECK[en]="Verifying system integrity..."
MSG_DOCKER_MISSING[en]="Docker not found — ZANA runs in SQLite-only mode (zero Docker required)."
MSG_PYTHON_MISSING[en]="Python 3.12+ not found. It is the nervous system of logic."
MSG_GIT_MISSING[en]="Git not found. Required to clone the Cortex."
MSG_UV_INSTALLING[en]="Installing 'uv' (neural-speed Python manager)..."
MSG_RUST_INSTALLING[en]="Rust not found — installing via rustup..."
MSG_RUST_OK[en]="Rust ready."
MSG_FORGING[en]="Forging CLI tools..."
MSG_SUCCESS[en]="ZANA v3.0.0 — INSTALLED SUCCESSFULLY."
MSG_STARTING[en]="Launching Aeon initialization wizard (zana init)..."
MSG_SOVEREIGNTY[en]="YOUR COGNITIVE SOVEREIGNTY HAS AWAKENED."
MSG_MODE_PROMPT[en]="Choose installation mode:"
MSG_MODE_UPDATE[en]="  [Enter]  Update code only  (your Aeon data is preserved)  ← default"
MSG_MODE_FULL[en]="  [F]      Full reset         (wipes all Aeon data — fresh start)"
MSG_MODE_CONFIRM[en]="⚠  Full reset: this permanently deletes your Aeon, memories, and WisdomRules. Continue? [y/N]"
MSG_DATA_WIPED[en]="Aeon data wiped. Starting fresh."

# ── Español ───────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[es]="Selecciona tu idioma / Select your language:"
MSG_WELCOME[es]="ZANA EN LÍNEA. Inicializando Protocolo de Soberanía..."
MSG_DEP_CHECK[es]="Verificando integridad del sistema..."
MSG_DOCKER_MISSING[es]="Docker no detectado — ZANA funciona en modo SQLite (no requiere Docker)."
MSG_PYTHON_MISSING[es]="Python 3.12+ no encontrado. Es el sistema nervioso de la lógica."
MSG_GIT_MISSING[es]="Git no encontrado. Necesario para clonar el Córtex."
MSG_UV_INSTALLING[es]="Instalando 'uv' (gestor de Python de alta velocidad)..."
MSG_RUST_INSTALLING[es]="Rust no detectado — instalando via rustup..."
MSG_RUST_OK[es]="Rust listo."
MSG_FORGING[es]="Forjando herramientas CLI..."
MSG_SUCCESS[es]="ZANA v3.0.0 — INSTALADA CON ÉXITO."
MSG_STARTING[es]="Iniciando asistente de creación del Aeón (zana init)..."
MSG_SOVEREIGNTY[es]="TU SOBERANÍA COGNITIVA HA DESPERTADO."
MSG_MODE_PROMPT[es]="Elige el modo de instalación:"
MSG_MODE_UPDATE[es]="  [Enter]  Solo código      (tu Aeón y datos se conservan)  ← por defecto"
MSG_MODE_FULL[es]="  [F]      Reinicio total   (borra todos los datos del Aeón)"
MSG_MODE_CONFIRM[es]="⚠  Reinicio total: esto elimina permanentemente tu Aeón, memorias y WisdomRules. ¿Continuar? [s/N]"
MSG_DATA_WIPED[es]="Datos del Aeón eliminados. Comenzando desde cero."

# ── Português ─────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[pt]="Selecione seu idioma / Select your language:"
MSG_WELCOME[pt]="ZANA ON-LINE. Inicializando Protocolo Soberano..."
MSG_DEP_CHECK[pt]="Verificando integridade do sistema..."
MSG_DOCKER_MISSING[pt]="Docker não encontrado — ZANA funciona em modo SQLite (sem Docker)."
MSG_PYTHON_MISSING[pt]="Python 3.12+ não encontrado. É o sistema nervoso da lógica."
MSG_GIT_MISSING[pt]="Git não encontrado. Necessário para clonar o Córtex."
MSG_UV_INSTALLING[pt]="Instalando 'uv' (gerenciador Python de alta velocidade)..."
MSG_RUST_INSTALLING[pt]="Rust não detectado — instalando via rustup..."
MSG_RUST_OK[pt]="Rust pronto."
MSG_FORGING[pt]="Forjando ferramentas CLI..."
MSG_SUCCESS[pt]="ZANA v3.0.0 — INSTALADA COM SUCESSO."
MSG_STARTING[pt]="Iniciando assistente de criação do Aeon (zana init)..."
MSG_SOVEREIGNTY[pt]="SUA SOBERANIA COGNITIVA DESPERTOU."
MSG_MODE_PROMPT[pt]="Escolha o modo de instalação:"
MSG_MODE_UPDATE[pt]="  [Enter]  Só código        (seu Aeon e dados são preservados)  ← padrão"
MSG_MODE_FULL[pt]="  [F]      Reset completo   (apaga todos os dados do Aeon)"
MSG_MODE_CONFIRM[pt]="⚠  Reset completo: isso exclui permanentemente seu Aeon, memórias e WisdomRules. Continuar? [s/N]"
MSG_DATA_WIPED[pt]="Dados do Aeon apagados. Começando do zero."

# ── Français ──────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[fr]="Choisissez votre langue / Select your language:"
MSG_WELCOME[fr]="ZANA EN LIGNE. Initialisation du Protocole Souverain..."
MSG_DEP_CHECK[fr]="Vérification de l'intégrité du système..."
MSG_DOCKER_MISSING[fr]="Docker non trouvé — ZANA fonctionne en mode SQLite (sans Docker)."
MSG_PYTHON_MISSING[fr]="Python 3.12+ non trouvé. C'est le système nerveux de la logique."
MSG_GIT_MISSING[fr]="Git non trouvé. Nécessaire pour cloner le Cortex."
MSG_UV_INSTALLING[fr]="Installation de 'uv' (gestionnaire Python haute performance)..."
MSG_RUST_INSTALLING[fr]="Rust non détecté — installation via rustup..."
MSG_RUST_OK[fr]="Rust prêt."
MSG_FORGING[fr]="Forge des outils CLI..."
MSG_SUCCESS[fr]="ZANA v3.0.0 — INSTALLÉE AVEC SUCCÈS."
MSG_STARTING[fr]="Lancement de l'assistant de création Aeon (zana init)..."
MSG_SOVEREIGNTY[fr]="VOTRE SOUVERAINETÉ COGNITIVE S'EST ÉVEILLÉE."
MSG_MODE_PROMPT[fr]="Choisissez le mode d'installation :"
MSG_MODE_UPDATE[fr]="  [Entrée]  Code seulement  (votre Aeon et données sont préservés)  ← défaut"
MSG_MODE_FULL[fr]="  [F]        Reset complet   (efface toutes les données Aeon)"
MSG_MODE_CONFIRM[fr]="⚠  Reset complet : ceci supprime définitivement votre Aeon, mémoires et WisdomRules. Continuer ? [o/N]"
MSG_DATA_WIPED[fr]="Données Aeon effacées. Nouveau départ."

# ── Italiano ──────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[it]="Seleziona la tua lingua / Select your language:"
MSG_WELCOME[it]="ZANA ONLINE. Inizializzazione del Protocollo Sovrano..."
MSG_DEP_CHECK[it]="Verifica dell'integrità del sistema..."
MSG_DOCKER_MISSING[it]="Docker non trovato — ZANA funziona in modalità SQLite (senza Docker)."
MSG_PYTHON_MISSING[it]="Python 3.12+ non trovato. È il sistema nervoso della logica."
MSG_GIT_MISSING[it]="Git non trovato. Necessario per clonare il Cortex."
MSG_UV_INSTALLING[it]="Installazione di 'uv' (gestore Python ad alta velocità)..."
MSG_RUST_INSTALLING[it]="Rust non rilevato — installazione via rustup..."
MSG_RUST_OK[it]="Rust pronto."
MSG_FORGING[it]="Forgiatura degli strumenti CLI..."
MSG_SUCCESS[it]="ZANA v3.0.0 — INSTALLATA CON SUCCESSO."
MSG_STARTING[it]="Avvio dell'assistente di creazione Aeon (zana init)..."
MSG_SOVEREIGNTY[it]="LA TUA SOVRANITÀ COGNITIVA SI È RISVEGLIATA."
MSG_MODE_PROMPT[it]="Scegli la modalità di installazione:"
MSG_MODE_UPDATE[it]="  [Invio]   Solo codice     (il tuo Aeon e i dati sono preservati)  ← predefinito"
MSG_MODE_FULL[it]="  [F]        Reset completo  (cancella tutti i dati Aeon)"
MSG_MODE_CONFIRM[it]="⚠  Reset completo: questo elimina definitivamente il tuo Aeon, memorie e WisdomRules. Continuare? [s/N]"
MSG_DATA_WIPED[it]="Dati Aeon cancellati. Inizio da zero."

# ── Deutsch ───────────────────────────────────────────────────────────────────
MSG_LANG_PROMPT[de]="Sprache wählen / Select your language:"
MSG_WELCOME[de]="ZANA ONLINE. Initialisierung des Souveränen Protokolls..."
MSG_DEP_CHECK[de]="Systemintegrität wird überprüft..."
MSG_DOCKER_MISSING[de]="Docker nicht gefunden — ZANA läuft im SQLite-Modus (kein Docker erforderlich)."
MSG_PYTHON_MISSING[de]="Python 3.12+ nicht gefunden. Es ist das Nervensystem der Logik."
MSG_GIT_MISSING[de]="Git nicht gefunden. Erforderlich zum Klonen des Kortex."
MSG_UV_INSTALLING[de]="Installation von 'uv' (Python-Manager mit neuronaler Geschwindigkeit)..."
MSG_RUST_INSTALLING[de]="Rust nicht gefunden — Installation über rustup..."
MSG_RUST_OK[de]="Rust bereit."
MSG_FORGING[de]="CLI-Werkzeuge werden geschmiedet..."
MSG_SUCCESS[de]="ZANA v3.0.0 — ERFOLGREICH INSTALLIERT."
MSG_STARTING[de]="Aeon-Erstellungsassistent wird gestartet (zana init)..."
MSG_SOVEREIGNTY[de]="DEINE KOGNITIVE SOUVERÄNITÄT IST ERWACHT."
MSG_MODE_PROMPT[de]="Installationsmodus wählen:"
MSG_MODE_UPDATE[de]="  [Enter]   Nur Code         (dein Aeon und Daten bleiben erhalten)  ← Standard"
MSG_MODE_FULL[de]="  [F]        Vollständiger Reset  (löscht alle Aeon-Daten)"
MSG_MODE_CONFIRM[de]="⚠  Vollständiger Reset: löscht dauerhaft deinen Aeon, Erinnerungen und WisdomRules. Fortfahren? [j/N]"
MSG_DATA_WIPED[de]="Aeon-Daten gelöscht. Neustart."

# ── Banner — ASCII Art ────────────────────────────────────────────────────────
banner() {
    clear
    echo -e "${MAGENTA}${BOLD}"
    cat << 'ASCIIART'

  ███████╗ █████╗ ███╗  ██╗ █████╗
     ███╔╝██╔══██╗████╗ ██║██╔══██╗
    ███╔╝  ███████║██╔██╗██║███████║
   ███╔╝   ██╔══██║██║╚████║██╔══██║
  ███████╗ ██║  ██║██║ ╚███║██║  ██║
  ╚══════╝ ╚═╝  ╚═╝╚═╝  ╚══╝╚═╝  ╚═╝

          Zero Autonomous Neural Architecture

                     ▲
                    ███
                   █████
                  ███████
                 █████████
                ███████████
               ▔▔▔▔▔▔▔▔▔▔▔▔▔

ASCIIART
    echo -e "${RESET}"
}

# ── Language selection ────────────────────────────────────────────────────────
select_language() {
    # In non-interactive / CI mode: respect ZANA_LANG env var, else auto-detect
    if [ -n "${ZANA_NON_INTERACTIVE:-}" ]; then
        if [ -z "${ZANA_LANG:-}" ]; then
            case "${LANG:-}" in
                es*) LANGUAGE="es" ;;
                pt*) LANGUAGE="pt" ;;
                fr*) LANGUAGE="fr" ;;
                it*) LANGUAGE="it" ;;
                de*) LANGUAGE="de" ;;
                *)   LANGUAGE="en" ;;
            esac
        fi
        return
    fi

    echo -e "${CYAN}  Select your language:${RESET}\n"
    echo -e "  ${BOLD}1${RESET}  English     ${DIM}← default${RESET}"
    echo -e "  ${BOLD}2${RESET}  Español"
    echo -e "  ${BOLD}3${RESET}  Português"
    echo -e "  ${BOLD}4${RESET}  Français"
    echo -e "  ${BOLD}5${RESET}  Italiano"
    echo -e "  ${BOLD}6${RESET}  Deutsch"
    echo
    read -r -t 30 -p "  [1-6 or Enter] > " LANG_INPUT </dev/tty || true
    echo

    case "${LANG_INPUT:-1}" in
        2|es|ES) LANGUAGE="es" ;;
        3|pt|PT) LANGUAGE="pt" ;;
        4|fr|FR) LANGUAGE="fr" ;;
        5|it|IT) LANGUAGE="it" ;;
        6|de|DE) LANGUAGE="de" ;;
        *)       LANGUAGE="en" ;;
    esac
}

# ── Install mode selection ────────────────────────────────────────────────────
select_install_mode() {
    if [ -n "${ZANA_NON_INTERACTIVE:-}" ]; then
        return
    fi
    if [ "${ZANA_FULL_RESET}" = "true" ]; then
        _confirm_full_reset
        return
    fi

    echo -e "${CYAN}  ${MSG_MODE_PROMPT[$LANGUAGE]}${RESET}\n"
    echo -e "${MSG_MODE_UPDATE[$LANGUAGE]}"
    echo -e "${YELLOW}${MSG_MODE_FULL[$LANGUAGE]}${RESET}"
    echo
    read -r -p "  > " MODE_INPUT </dev/tty || true
    echo

    case "${MODE_INPUT,,}" in
        f|full) ZANA_FULL_RESET=true; _confirm_full_reset ;;
        *)      ZANA_FULL_RESET=false ;;
    esac
}

_confirm_full_reset() {
    local ZANA_DATA="$HOME/.zana"
    local CONFIRM_WORD="DELETE"

    echo
    echo -e "${RED}${BOLD}  ╔══════════════════════════════════════════════════════╗${RESET}"
    echo -e "${RED}${BOLD}  ║   ⚠  FULL RESET — PERMANENT DATA LOSS WARNING  ⚠   ║${RESET}"
    echo -e "${RED}${BOLD}  ╚══════════════════════════════════════════════════════╝${RESET}"
    echo
    echo -e "${YELLOW}  The following will be permanently deleted:${RESET}"
    echo -e "${DIM}    $ZANA_DATA/aeon              (your Aeon identity)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/episodic.db       (episodic memory)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/wisdom_rules       (accumulated WisdomRules)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/civic_ledger       (SHA-256 audit trail)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/semantic           (semantic memory)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/world_model        (world model)${RESET}"
    echo -e "${DIM}    $ZANA_DATA/skills_registry.json${RESET}"
    echo -e "${DIM}    $ZANA_DATA/zana_config.json${RESET}"
    echo

    # ── Offer automatic backup ────────────────────────────────────────────────
    local HAS_DATA=false
    for path in "$ZANA_DATA/aeon" "$ZANA_DATA/episodic.db" "$ZANA_DATA/wisdom_rules"; do
        [ -e "$path" ] && HAS_DATA=true && break
    done

    if $HAS_DATA; then
        echo -e "${CYAN}  Would you like to create a backup before wiping? [Y/n]${RESET}"
        read -r -p "  > " BACKUP_INPUT </dev/tty || true
        echo
        case "${BACKUP_INPUT,,}" in
            n|no|nein|non|não)
                echo -e "${YELLOW}  Backup skipped.${RESET}\n" ;;
            *)
                _backup_aeon_data ;;
        esac
    fi

    # ── Final confirmation — must type DELETE ─────────────────────────────────
    echo -e "${RED}  This action CANNOT be undone (unless you made a backup above).${RESET}"
    echo -e "${RED}  Type ${BOLD}${CONFIRM_WORD}${RESET}${RED} to confirm, or anything else to cancel:${RESET}"
    read -r -p "  > " CONFIRM </dev/tty || true
    echo

    if [ "${CONFIRM}" = "${CONFIRM_WORD}" ]; then
        _wipe_aeon_data
    else
        echo -e "${GREEN}  ✓ Cancelled — switching to update-only mode. Your Aeon is safe.${RESET}\n"
        ZANA_FULL_RESET=false
    fi
}

_backup_aeon_data() {
    local ZANA_DATA="$HOME/.zana"
    local TIMESTAMP
    TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
    local BACKUP_DIR="$HOME/.zana_backup_$TIMESTAMP"

    echo -e "${CYAN}  ▶ Creating backup at ${BOLD}$BACKUP_DIR${RESET}${CYAN}...${RESET}"
    mkdir -p "$BACKUP_DIR"

    for item in aeon episodic.db wisdom_rules civic_ledger semantic world_model \
                skills_registry.json zana_config.json; do
        [ -e "$ZANA_DATA/$item" ] && cp -r "$ZANA_DATA/$item" "$BACKUP_DIR/" 2>/dev/null || true
    done

    echo -e "${GREEN}  ✓ Backup saved → $BACKUP_DIR${RESET}"
    echo -e "${DIM}    (restore anytime by copying back to $ZANA_DATA/)${RESET}\n"
}

_wipe_aeon_data() {
    local ZANA_DATA="$HOME/.zana"
    echo -e "${YELLOW}  ▶ Wiping Aeon data...${RESET}"
    rm -rf \
        "$ZANA_DATA/aeon" \
        "$ZANA_DATA/episodic.db" \
        "$ZANA_DATA/skills_registry.json" \
        "$ZANA_DATA/wisdom_rules" \
        "$ZANA_DATA/civic_ledger" \
        "$ZANA_DATA/world_model" \
        "$ZANA_DATA/semantic" \
        "$ZANA_DATA/zana_config.json" \
        2>/dev/null || true
    echo -e "${GREEN}  ✓ ${MSG_DATA_WIPED[$LANGUAGE]}${RESET}\n"
}

# ── Dependency checks ─────────────────────────────────────────────────────────
check_dependencies() {
    echo -e "${CYAN}  ▶ ${MSG_DEP_CHECK[$LANGUAGE]}${RESET}\n"

    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}  ✗ ${MSG_PYTHON_MISSING[$LANGUAGE]}${RESET}"
        echo -e "${YELLOW}    → https://python.org${RESET}"
        exit 1
    fi

    if ! command -v git &>/dev/null; then
        echo -e "${RED}  ✗ ${MSG_GIT_MISSING[$LANGUAGE]}${RESET}"
        exit 1
    fi

    if ! command -v docker &>/dev/null; then
        echo -e "${YELLOW}  ⚠ ${MSG_DOCKER_MISSING[$LANGUAGE]}${RESET}"
    fi

    if ! command -v uv &>/dev/null; then
        echo -e "${CYAN}  ▶ ${MSG_UV_INSTALLING[$LANGUAGE]}${RESET}"
        curl -LsSf https://astral.sh/uv/install.sh | bash
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if ! command -v cargo &>/dev/null && [ ! -f "$HOME/.cargo/bin/cargo" ]; then
        echo -e "${CYAN}  ▶ ${MSG_RUST_INSTALLING[$LANGUAGE]}${RESET}"
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
        export PATH="$HOME/.cargo/bin:$PATH"
        echo -e "${GREEN}  ✓ ${MSG_RUST_OK[$LANGUAGE]}${RESET}"
    else
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    if ! command -v cc &>/dev/null && command -v apt-get &>/dev/null; then
        echo -e "${CYAN}  ▶ Installing build-essential (gcc linker for Rust)...${RESET}"
        sudo apt-get install -y build-essential > /dev/null 2>&1 || true
    fi

    echo
}

# ── Core install ──────────────────────────────────────────────────────────────
install_core() {
    echo -e "${CYAN}  ▶ ${MSG_FORGING[$LANGUAGE]}${RESET}"
    ZANA_REPO_DIR="$HOME/.zana/core-repo"

    if [ -d "cli" ] && [ -d "sensory" ]; then
        echo -e "${DIM}    (local dev environment detected)${RESET}"
        ZANA_REPO_DIR="$(pwd)"
    else
        echo -e "${CYAN}  ▶ Cloning/updating repository...${RESET}"
        mkdir -p "$HOME/.zana"
        if [ -d "$ZANA_REPO_DIR" ] && ! git -C "$ZANA_REPO_DIR" rev-parse --git-dir &>/dev/null; then
            echo -e "${YELLOW}  ⚠ Stale directory — re-cloning...${RESET}"
            if command -v sudo &>/dev/null; then
                sudo rm -rf "$ZANA_REPO_DIR" || rm -rf "$ZANA_REPO_DIR"
            else
                rm -rf "$ZANA_REPO_DIR"
            fi
        fi
        if [ ! -d "$ZANA_REPO_DIR" ]; then
            git clone "https://github.com/$REPO.git" "$ZANA_REPO_DIR" --quiet
        else
            git -C "$ZANA_REPO_DIR" fetch --all --quiet
            git -C "$ZANA_REPO_DIR" reset --hard origin/main --quiet
        fi
    fi

    echo -e "${CYAN}  ▶ Deploying ZANA CLI v3.0.0...${RESET}"
    uv tool uninstall zana 2>/dev/null || true
    uv tool install "$ZANA_REPO_DIR/cli" --force --quiet
    echo -e "${GREEN}  ✓ CLI installed.${RESET}\n"

    export ZANA_CORE_DIR="$ZANA_REPO_DIR"
}

# ── Configure shell PATH ──────────────────────────────────────────────────────
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
    fi

    if ! grep -q "ZANA_CORE_DIR" "$shell_rc"; then
        echo "export ZANA_CORE_DIR=\"$ZANA_CORE_DIR\"" >> "$shell_rc"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
select_language

echo -e "${MAGENTA}${BOLD}  ${MSG_WELCOME[$LANGUAGE]}${RESET}\n"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"

select_install_mode
check_dependencies
install_core
configure_path

echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  ✓ ${MSG_SUCCESS[$LANGUAGE]}${RESET}"
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "\n  ${MAGENTA}${BOLD}${MSG_SOVEREIGNTY[$LANGUAGE]}${RESET}\n"

echo -e "${CYAN}  ▶ ${MSG_STARTING[$LANGUAGE]}${RESET}"
sleep 1

# Reconnect stdin to the real terminal before the interactive onboarding wizard.
# curl|bash pipes stdin through curl, destroying the TTY for subprocesses.
# exec < /dev/tty restores it (same fix used by rustup, nvm, Homebrew).
# In headless/CI environments without /dev/tty, fall back to non-interactive mode.
if [ -z "${ZANA_NON_INTERACTIVE:-}" ]; then
    if [ -e /dev/tty ] && (true < /dev/tty) 2>/dev/null; then
        exec < /dev/tty
    else
        export ZANA_NON_INTERACTIVE=1
    fi
fi

# Run the zero-friction Aeon initialization wizard (not `zana start` which requires Docker).
# After init, the user can run `zana start` manually if they want the full Docker stack.
"$ZANA_INSTALL_DIR/zana" init
