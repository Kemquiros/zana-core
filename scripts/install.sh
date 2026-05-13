#!/usr/bin/env bash
# =============================================================================
#  ZANA CLI — Instalador Universal / Universal Installer
#  Uso / Usage: curl -LsSf https://raw.githubusercontent.com/Kemquiros/zana-core/main/scripts/install.sh | sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Colores / Colors
# ---------------------------------------------------------------------------
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
MAGENTA='\033[35m'
RESET='\033[0m'

info()    { printf "${MAGENTA}[ZANA]${RESET}  %s\n" "$*"; }
success() { printf "${GREEN}[OK]${RESET}    %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
error()   { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Banner
# ---------------------------------------------------------------------------
printf "${MAGENTA}"
cat << 'BANNER'

  ███████╗ █████╗ ███╗   ██╗ █████╗
  ╚══███╔╝██╔══██╗████╗  ██║██╔══██╗
    ███╔╝ ███████║██╔██╗ ██║███████║
   ███╔╝  ██╔══██║██║╚██╗██║██╔══██║
  ███████╗██║  ██║██║ ╚████║██║  ██║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝

  Zero Autonomous Neural Architecture
  CLI Installer v1.0 — vecanova-zana
BANNER
printf "${RESET}\n"

info "Iniciando instalación... (Starting installation...)"
info "Fecha / Date: $(date '+%Y-%m-%d %H:%M:%S')"
printf "\n"

# ---------------------------------------------------------------------------
# Advertencia si se ejecuta como root (warn but continue)
# ---------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
  warn "Ejecutando como root. Se recomienda usar un usuario normal."
  warn "Running as root. It is recommended to use a regular user account."
fi

# ---------------------------------------------------------------------------
# 2. Detección de OS / OS Detection
# ---------------------------------------------------------------------------
OS=""
DISTRO=""
PKG_MANAGER=""

case "$(uname -s)" in
  Linux*)
    OS="linux"
    if [ -f /etc/os-release ]; then
      # shellcheck source=/dev/null
      . /etc/os-release
      DISTRO="${ID:-unknown}"
    fi
    if command -v apt-get >/dev/null 2>&1; then
      PKG_MANAGER="apt"
    elif command -v dnf >/dev/null 2>&1; then
      PKG_MANAGER="dnf"
    elif command -v pacman >/dev/null 2>&1; then
      PKG_MANAGER="pacman"
    else
      PKG_MANAGER="unknown"
    fi
    ;;
  Darwin*)
    OS="macos"
    PKG_MANAGER="brew"
    ;;
  *)
    error "Sistema operativo no soportado: $(uname -s). / Unsupported OS: $(uname -s)."
    ;;
esac

info "Sistema detectado / Detected OS: ${OS} (${DISTRO:-native}) — gestor: ${PKG_MANAGER}"

# ---------------------------------------------------------------------------
# Helper: verifica si un binario existe / check binary exists
# ---------------------------------------------------------------------------
has_cmd() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------------------
# Helper: versión de python como entero comparable (3.12 → 312)
# ---------------------------------------------------------------------------
python_version_int() {
  "$1" -c "import sys; print(sys.version_info.major * 100 + sys.version_info.minor)" 2>/dev/null || echo "0"
}

# ---------------------------------------------------------------------------
# Helper: instala pyenv como fallback universal
# ---------------------------------------------------------------------------
install_pyenv_python() {
  warn "Usando fallback universal: instalando pyenv... (Using universal fallback: installing pyenv...)"

  if ! has_cmd pyenv; then
    info "Descargando pyenv... (Downloading pyenv...)"
    export PYENV_ROOT="${HOME}/.pyenv"
    curl -fsSL https://pyenv.run | bash || error "Falló la instalación de pyenv. / pyenv installation failed."

    # Activar pyenv en la sesión actual
    export PYENV_ROOT="${HOME}/.pyenv"
    export PATH="${PYENV_ROOT}/bin:${PATH}"
    eval "$(pyenv init -)" 2>/dev/null || true
    eval "$(pyenv virtualenv-init -)" 2>/dev/null || true
  else
    export PYENV_ROOT="${HOME}/.pyenv"
    export PATH="${PYENV_ROOT}/bin:${PATH}"
    eval "$(pyenv init -)" 2>/dev/null || true
  fi

  info "Instalando Python 3.12 via pyenv... (Installing Python 3.12 via pyenv...)"
  pyenv install -s 3.12 || error "pyenv no pudo instalar Python 3.12. / pyenv failed to install Python 3.12."
  pyenv global 3.12
  success "Python 3.12 instalado via pyenv. / Python 3.12 installed via pyenv."
}

# ---------------------------------------------------------------------------
# 3. Check / Install Python 3.12+
# ---------------------------------------------------------------------------
printf "\n"
info "=== Paso 1/5: Verificando Python 3.12+ / Step 1/5: Checking Python 3.12+ ==="

PYTHON_BIN=""

# Candidatos en orden de preferencia
for candidate in python3.12 python3.13 python3.14 python3 python; do
  if has_cmd "$candidate"; then
    ver=$(python_version_int "$candidate")
    if [ "$ver" -ge 312 ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [ -n "$PYTHON_BIN" ]; then
  PY_VER=$("$PYTHON_BIN" --version 2>&1)
  success "Python compatible encontrado / Compatible Python found: ${PY_VER} → ${PYTHON_BIN}"
else
  warn "Python 3.12+ no encontrado. Instalando... / Python 3.12+ not found. Installing..."

  case "${OS}" in
    macos)
      if ! has_cmd brew; then
        error "Homebrew no está instalado. Instálalo primero: https://brew.sh / Homebrew not found. Install it first: https://brew.sh"
      fi
      info "brew install python@3.12"
      brew install python@3.12 || install_pyenv_python
      ;;
    linux)
      case "${PKG_MANAGER}" in
        apt)
          info "apt-get install python3.12 python3.12-venv python3.12-pip"
          sudo apt-get update -qq
          sudo apt-get install -y python3.12 python3.12-venv python3.12-pip 2>/dev/null \
            || { warn "apt falló. Intentando pyenv... / apt failed. Trying pyenv..."; install_pyenv_python; }
          ;;
        dnf)
          info "dnf install python3.12"
          sudo dnf install -y python3.12 2>/dev/null \
            || { warn "dnf falló. Intentando pyenv... / dnf failed. Trying pyenv..."; install_pyenv_python; }
          ;;
        pacman)
          info "pacman -S python"
          sudo pacman -Sy --noconfirm python 2>/dev/null \
            || { warn "pacman falló. Intentando pyenv... / pacman failed. Trying pyenv..."; install_pyenv_python; }
          ;;
        *)
          install_pyenv_python
          ;;
      esac
      ;;
  esac

  # Re-buscar tras instalación
  for candidate in python3.12 python3.13 python3.14 python3 python; do
    if has_cmd "$candidate"; then
      ver=$(python_version_int "$candidate")
      if [ "$ver" -ge 312 ]; then
        PYTHON_BIN="$candidate"
        break
      fi
    fi
  done

  # Buscar también en pyenv shims
  if [ -z "$PYTHON_BIN" ] && [ -d "${HOME}/.pyenv/shims" ]; then
    export PATH="${HOME}/.pyenv/shims:${HOME}/.pyenv/bin:${PATH}"
    for candidate in python3.12 python3 python; do
      if has_cmd "$candidate"; then
        ver=$(python_version_int "$candidate")
        if [ "$ver" -ge 312 ]; then
          PYTHON_BIN="$candidate"
          break
        fi
      fi
    done
  fi

  [ -n "$PYTHON_BIN" ] || error "No se pudo instalar Python 3.12+. Instálalo manualmente: https://www.python.org/downloads/ / Could not install Python 3.12+. Install manually: https://www.python.org/downloads/"
  PY_VER=$("$PYTHON_BIN" --version 2>&1)
  success "Python instalado / Python installed: ${PY_VER}"
fi

# ---------------------------------------------------------------------------
# 4. Check / Install pipx
# ---------------------------------------------------------------------------
printf "\n"
info "=== Paso 2/5: Verificando pipx / Step 2/5: Checking pipx ==="

if has_cmd pipx; then
  success "pipx ya está instalado / pipx already installed: $(pipx --version 2>/dev/null || echo 'OK')"
else
  warn "pipx no encontrado. Instalando... / pipx not found. Installing..."
  "$PYTHON_BIN" -m pip install --user pipx \
    || error "No se pudo instalar pipx. Instálalo manualmente: pip install --user pipx / Could not install pipx. Install manually: pip install --user pipx"

  # Activar pipx en la sesión actual
  export PATH="${HOME}/.local/bin:${PATH}"

  has_cmd pipx || error "pipx instalado pero no encontrado en PATH. Reinicia tu terminal. / pipx installed but not in PATH. Restart your terminal."
  success "pipx instalado correctamente / pipx installed: $(pipx --version 2>/dev/null || echo 'OK')"
fi

# ---------------------------------------------------------------------------
# 5. Asegurar ~/.local/bin en PATH (Fix PATH)
# ---------------------------------------------------------------------------
printf "\n"
info "=== Paso 3/5: Asegurando PATH / Step 3/5: Ensuring PATH ==="

LOCAL_BIN="${HOME}/.local/bin"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

add_to_file_if_missing() {
  local file="$1"
  local line="$2"
  if [ -f "$file" ]; then
    if ! grep -qF "${LOCAL_BIN}" "$file" 2>/dev/null; then
      printf '\n# Added by ZANA installer\n%s\n' "$line" >> "$file"
      info "PATH añadido a / PATH added to: ${file}"
    else
      info "PATH ya presente en / PATH already present in: ${file}"
    fi
  fi
}

add_to_file_if_missing "${HOME}/.bashrc"  "${PATH_LINE}"
add_to_file_if_missing "${HOME}/.zshrc"   "${PATH_LINE}"
add_to_file_if_missing "${HOME}/.profile" "${PATH_LINE}"

# Activar en sesión actual
export PATH="${LOCAL_BIN}:${PATH}"
success "PATH actualizado para esta sesión / PATH updated for current session."

# ---------------------------------------------------------------------------
# 6. Install / Upgrade vecanova-zana via pipx
# ---------------------------------------------------------------------------
printf "\n"
info "=== Paso 4/5: Instalando vecanova-zana / Step 4/5: Installing vecanova-zana ==="

if pipx list 2>/dev/null | grep -q "vecanova-zana"; then
  info "vecanova-zana ya instalado. Actualizando... / Already installed. Upgrading..."
  pipx upgrade vecanova-zana \
    || error "No se pudo actualizar vecanova-zana. / Could not upgrade vecanova-zana."
  success "vecanova-zana actualizado / vecanova-zana upgraded."
else
  info "Instalando vecanova-zana desde PyPI... / Installing vecanova-zana from PyPI..."
  pipx install vecanova-zana \
    || error "No se pudo instalar vecanova-zana. Verifica tu conexión e inténtalo de nuevo. / Could not install vecanova-zana. Check your connection and try again."
  success "vecanova-zana instalado / vecanova-zana installed."
fi

# ---------------------------------------------------------------------------
# 7. Verificar que `zana` está en PATH / Verify `zana` is in PATH
# ---------------------------------------------------------------------------
printf "\n"
info "=== Paso 5/5: Verificando instalación / Step 5/5: Verifying installation ==="

if ! has_cmd zana; then
  # pipx ensurepath como último recurso
  pipx ensurepath 2>/dev/null || true
  export PATH="${LOCAL_BIN}:${PATH}"
fi

if has_cmd zana; then
  ZANA_VER=$(zana --version 2>/dev/null || echo "desconocida / unknown")
  success "zana encontrado en PATH / zana found in PATH — versión: ${ZANA_VER}"
else
  warn "El binario 'zana' no se detectó en PATH automáticamente."
  warn "The 'zana' binary was not detected in PATH automatically."
  warn "Ejecuta en tu terminal / Run in your terminal:"
  warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  warn "  zana init"
  # No se aborta aquí — el binario puede estar disponible tras reiniciar la shell
fi

# ---------------------------------------------------------------------------
# 8. Lanzar zana init / Launch zana init
# ---------------------------------------------------------------------------
printf "\n"
info "Ejecutando 'zana init' para configurar tu entorno... / Running 'zana init' to configure your environment..."

if has_cmd zana; then
  zana init || warn "'zana init' retornó un error. Puedes ejecutarlo manualmente. / 'zana init' returned an error. You can run it manually."
else
  warn "Ejecuta manualmente / Run manually: zana init"
fi

# ---------------------------------------------------------------------------
# 9. Mensaje final de éxito / Final success message
# ---------------------------------------------------------------------------
printf "\n"
printf "${GREEN}"
cat << 'SUCCESS_BANNER'
  ╔══════════════════════════════════════════════════╗
  ║   ZANA CLI instalada y lista / Installed & Ready  ║
  ╚══════════════════════════════════════════════════╝
SUCCESS_BANNER
printf "${RESET}\n"

printf "  ${GREEN}→${RESET} Empieza con / Get started with:  ${MAGENTA}zana --help${RESET}\n"
printf "  ${GREEN}→${RESET} Documentación / Docs:             ${MAGENTA}https://github.com/vecanova/zana-core${RESET}\n"
printf "\n"
printf "  ${MAGENTA}JUNTOS HACEMOS TEMBLAR LOS CIELOS.${RESET}\n"
printf "\n"
