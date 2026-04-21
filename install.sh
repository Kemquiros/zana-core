#!/usr/bin/env bash
# ZANA Installer — Zero Autonomous Neural Architecture
# Usage: curl -LsSf https://raw.githubusercontent.com/kemquiros/zana-core/main/install.sh | sh
set -euo pipefail

BOLD='\033[1m'
RESET='\033[0m'
GREEN='\033[0;32m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'

ZANA_VERSION="${ZANA_VERSION:-latest}"
ZANA_INSTALL_DIR="${ZANA_INSTALL_DIR:-$HOME/.local/bin}"
REPO="kemquiros/zana-core"

banner() {
cat << 'EOF'

        [ Z A N A   I S   O N L I N E ]
     Zero Autonomous Neural Architecture
     Sovereign Cognitive Runtime v2.0.0

EOF
}

info()    { echo -e "${CYAN}  ▶ $*${RESET}"; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠ $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }

detect_os() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    case "$OS" in
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                PLATFORM="linux-wsl2"
            else
                PLATFORM="linux"
            fi
            ;;
        Darwin) PLATFORM="macos" ;;
        *) error "Unsupported OS: $OS. Install manually from https://github.com/$REPO/releases" ;;
    esac

    case "$ARCH" in
        x86_64|amd64) ARCH="x86_64" ;;
        aarch64|arm64) ARCH="aarch64" ;;
        *) error "Unsupported architecture: $ARCH" ;;
    esac
}

check_dependency() {
    local cmd="$1"
    local install_hint="$2"
    if ! command -v "$cmd" &>/dev/null; then
        warn "$cmd not found. $install_hint"
        return 1
    fi
    return 0
}

install_uv() {
    info "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    success "uv installed."
}

install_python_cli() {
    info "Installing ZANA CLI via uv..."
    if ! command -v uv &>/dev/null; then
        install_uv
    fi

    if [ "$ZANA_VERSION" = "latest" ]; then
        uv tool install "zana @ git+https://github.com/$REPO.git#subdirectory=zana-core/cli" 2>/dev/null \
            || uv pip install --system zana 2>/dev/null \
            || true
    else
        uv pip install --system "zana==$ZANA_VERSION" 2>/dev/null || true
    fi

    # Fallback: install from local directory if running inside the repo
    if [ -f "$(dirname "$0")/cli/pyproject.toml" ]; then
        info "Installing from local source..."
        uv tool install "$(dirname "$0")/cli" --force
    fi
}

ensure_in_path() {
    mkdir -p "$ZANA_INSTALL_DIR"
    if ! echo "$PATH" | grep -q "$ZANA_INSTALL_DIR"; then
        # Add to shell rc files
        for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
            if [ -f "$rc" ]; then
                if ! grep -q "$ZANA_INSTALL_DIR" "$rc"; then
                    echo "export PATH=\"$ZANA_INSTALL_DIR:\$PATH\"" >> "$rc"
                fi
            fi
        done
        export PATH="$ZANA_INSTALL_DIR:$PATH"
        warn "Added $ZANA_INSTALL_DIR to PATH. Restart your shell or run: export PATH=\"$ZANA_INSTALL_DIR:\$PATH\""
    fi
}

setup_docker_stack() {
    # When piped via curl | sh, BASH_SOURCE[0] is empty — fall back to $PWD
    local script_dir
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "bash" ]; then
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        script_dir="$PWD"
    fi

    if [ ! -f "$script_dir/docker-compose.yml" ]; then
        warn "docker-compose.yml not found. Docker stack setup skipped."
        warn "Clone the full repo to run the stack:"
        warn "  git clone https://github.com/$REPO && cd zana-core"
        return
    fi

    # Generate .env if missing
    if [ ! -f "$script_dir/.env" ]; then
        info "Generating .env from template..."
        cp "$script_dir/.env.example" "$script_dir/.env"
        sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 16)|" "$script_dir/.env"
        sed -i "s|^NEO4J_PASSWORD=.*|NEO4J_PASSWORD=$(openssl rand -hex 12)|" "$script_dir/.env"
        success ".env created. Add your LLM API keys to $script_dir/.env"
    fi

    set -a; source "$script_dir/.env"; set +a
    mkdir -p "$script_dir/data"/{chroma,postgres,redis,neo4j/data,caddy}
}

print_summary() {
    echo ""
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}  ZANA INSTALLED${RESET}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    echo -e "  ${BOLD}Quick start:${RESET}"
    echo -e "    ${CYAN}zana setup${RESET}     — first-run wizard (configure API keys)"
    echo -e "    ${CYAN}zana start${RESET}     — boot the full stack"
    echo -e "    ${CYAN}zana status${RESET}    — check all services + ZFI score"
    echo -e "    ${CYAN}zana chat${RESET}      — talk to ZANA"
    echo ""
    echo -e "  ${BOLD}Docs:${RESET} https://github.com/$REPO"
    echo ""
    echo -e "  ${MAGENTA}JUNTOS HACEMOS TEMBLAR LOS CIELOS.${RESET}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────

banner
detect_os
info "Platform: $PLATFORM / $ARCH"

# Check dependencies
MISSING_DOCKER=false
if ! check_dependency docker "Install from https://docs.docker.com/get-docker/"; then
    MISSING_DOCKER=true
fi

if ! check_dependency python3 "Install Python 3.12 from https://python.org/"; then
    warn "Python 3.12+ required for full functionality."
fi

ensure_in_path
install_python_cli

if command -v zana &>/dev/null; then
    success "ZANA CLI installed: $(zana --version 2>/dev/null || echo 'zana v2.0.0')"
else
    warn "CLI install may require restarting your shell."
fi

setup_docker_stack

if [ "$MISSING_DOCKER" = true ]; then
    warn "Docker not found. Install it, then run: zana start"
fi

print_summary
