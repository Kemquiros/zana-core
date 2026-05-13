#Requires -Version 5.1
<#
.SYNOPSIS
    ZANA CLI — Windows Installer (PowerShell 5.1+ / 7+)
.DESCRIPTION
    Instala ZANA CLI (vecanova-zana) via pipx en Windows 10/11.
    Uso: irm https://raw.githubusercontent.com/.../install.ps1 | iex
#>

# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

function Write-Info  { param($msg) Write-Host "[ZANA]  $msg" -ForegroundColor Magenta }
function Write-Ok    { param($msg) Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ─────────────────────────────────────────────────────────────
# PASO 1 — Set-ExecutionPolicy + Banner
# ─────────────────────────────────────────────────────────────

Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "  ███████╗ █████╗ ███╗   ██╗ █████╗ " -ForegroundColor Magenta
Write-Host "  ╚══███╔╝██╔══██╗████╗  ██║██╔══██╗" -ForegroundColor Magenta
Write-Host "    ███╔╝ ███████║██╔██╗ ██║███████║" -ForegroundColor Magenta
Write-Host "   ███╔╝  ██╔══██║██║╚██╗██║██╔══██║" -ForegroundColor Magenta
Write-Host "  ███████╗██║  ██║██║ ╚████║██║  ██║" -ForegroundColor Magenta
Write-Host "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝" -ForegroundColor Magenta
Write-Host "  Zero Autonomous Neural Architecture" -ForegroundColor Magenta
Write-Host "  Windows Installer — vecanova-zana" -ForegroundColor Magenta
Write-Host ""

# ─────────────────────────────────────────────────────────────
# PASO 2 — Advertencia si Admin
# ─────────────────────────────────────────────────────────────

try {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Warn "Ejecutando como Administrador. Se recomienda instalar como usuario normal."
        Write-Warn "Running as Administrator. It is recommended to install as a normal user."
    }
} catch {
    Write-Warn "No se pudo verificar el nivel de privilegios. Continuando..."
}

# ─────────────────────────────────────────────────────────────
# PASO 3 — Detectar / instalar Python 3.12+
# ─────────────────────────────────────────────────────────────

Write-Info "Buscando Python 3.12+ / Looking for Python 3.12+..."

$pythonExe   = $null
$pythonFound = $false

$candidates = @('python', 'python3', 'py')

foreach ($candidate in $candidates) {
    try {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }

        $args = if ($candidate -eq 'py') { @('-3.12', '-c', "import sys; print(sys.version_info[:2])") } `
                else { @('-c', "import sys; print(sys.version_info[:2])") }

        $verOutput = & $candidate @args 2>$null
        if ($verOutput -match '\((\d+),\s*(\d+)\)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                $pythonExe   = $candidate
                $pythonFound = $true
                Write-Ok "Python $major.$minor encontrado en: $($(Get-Command $candidate).Source)"
                break
            } else {
                Write-Warn "Python $major.$minor encontrado pero se requiere 3.12+."
            }
        }
    } catch {
        # Candidato no disponible, continuar
    }
}

if (-not $pythonFound) {
    Write-Info "Python 3.12+ no encontrado. Intentando instalar via winget..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) {
                Write-Fail "winget no pudo instalar Python. Instala manualmente: https://www.python.org/downloads/ y vuelve a ejecutar."
            }
        } catch {
            Write-Fail "Error al invocar winget: $_. Instala Python manualmente: https://www.python.org/downloads/"
        }
    } else {
        Write-Fail "winget no disponible. Instala Python 3.12+ manualmente desde: https://www.python.org/downloads/ y vuelve a ejecutar este script."
    }

    # Refrescar PATH en sesión actual
    $env:PATH = [System.Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + `
                [System.Environment]::GetEnvironmentVariable('PATH', 'User')

    # Re-detectar python
    foreach ($candidate in $candidates) {
        try {
            $args = if ($candidate -eq 'py') { @('-3.12', '-c', "import sys; print(sys.version_info[:2])") } `
                    else { @('-c', "import sys; print(sys.version_info[:2])") }

            $verOutput = & $candidate @args 2>$null
            if ($verOutput -match '\((\d+),\s*(\d+)\)') {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                    $pythonExe   = $candidate
                    $pythonFound = $true
                    Write-Ok "Python $major.$minor listo tras instalación."
                    break
                }
            }
        } catch { }
    }

    if (-not $pythonFound) {
        Write-Fail "Python 3.12+ sigue sin encontrarse. Reinicia la terminal y vuelve a ejecutar, o instala manualmente: https://www.python.org/downloads/"
    }
}

# ─────────────────────────────────────────────────────────────
# PASO 4 — Detectar / instalar pipx
# ─────────────────────────────────────────────────────────────

Write-Info "Verificando pipx..."

$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue

if ($pipxCmd) {
    Write-Ok "pipx ya instalado: $($pipxCmd.Source)"
} else {
    Write-Info "pipx no encontrado. Instalando via pip..."
    try {
        & $pythonExe -m pip install --user pipx
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "No se pudo instalar pipx. Verifica que pip esté disponible."
        }
        Write-Ok "pipx instalado correctamente."
    } catch {
        Write-Fail "Error al instalar pipx: $_"
    }

    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + `
                [System.Environment]::GetEnvironmentVariable('PATH', 'User')
}

# ─────────────────────────────────────────────────────────────
# PASO 5 — Fix PATH permanente
# ─────────────────────────────────────────────────────────────

Write-Info "Verificando y actualizando PATH de usuario..."

$pathDirs = @(
    "$env:APPDATA\Python\Python312\Scripts",
    "$env:APPDATA\Python\Scripts",
    "$env:USERPROFILE\.local\bin",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\Scripts"
)

foreach ($dir in $pathDirs) {
    try {
        $userPath = [System.Environment]::GetEnvironmentVariable('PATH', 'User')
        if ($null -eq $userPath) { $userPath = '' }

        if ($userPath -notlike "*$dir*") {
            $newPath = if ($userPath -eq '') { $dir } else { "$userPath;$dir" }
            [System.Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
            Write-Ok "Agregado a PATH: $dir"
        } else {
            Write-Info "Ya en PATH: $dir"
        }

        # Actualizar PATH de sesión actual también
        if ($env:PATH -notlike "*$dir*") {
            $env:PATH = "$env:PATH;$dir"
        }
    } catch {
        Write-Warn "No se pudo agregar $dir al PATH: $_"
    }
}

# Refresh completo desde registro
try {
    $env:PATH = [System.Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + `
                [System.Environment]::GetEnvironmentVariable('PATH', 'User')
} catch {
    Write-Warn "No se pudo refrescar PATH desde registro. Continuando..."
}

# ─────────────────────────────────────────────────────────────
# PASO 6 — Install / upgrade vecanova-zana
# ─────────────────────────────────────────────────────────────

Write-Info "Instalando/actualizando vecanova-zana via pipx..."

try {
    $pipxList = pipx list 2>$null
    if ($pipxList -match "vecanova-zana") {
        Write-Info "vecanova-zana ya instalado. Ejecutando upgrade..."
        pipx upgrade vecanova-zana
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "pipx upgrade reportó un error. Puede que ya esté en la versión más reciente."
        } else {
            Write-Ok "vecanova-zana actualizado correctamente."
        }
    } else {
        Write-Info "Instalando vecanova-zana por primera vez..."
        pipx install vecanova-zana
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "pipx install vecanova-zana falló. Verifica tu conexión a Internet y vuelve a intentar."
        }
        Write-Ok "vecanova-zana instalado correctamente."
    }
} catch {
    Write-Fail "Error al instalar/actualizar vecanova-zana: $_"
}

# ─────────────────────────────────────────────────────────────
# PASO 7 — Verificar `zana` en PATH
# ─────────────────────────────────────────────────────────────

Write-Info "Verificando que 'zana' esté disponible en PATH..."

$zanaCmd = Get-Command zana -ErrorAction SilentlyContinue

if (-not $zanaCmd) {
    Write-Info "'zana' no encontrado inmediatamente. Ejecutando pipx ensurepath..."
    try {
        pipx ensurepath
    } catch {
        Write-Warn "pipx ensurepath falló: $_"
    }

    # Refresh PATH
    try {
        $env:PATH = [System.Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + `
                    [System.Environment]::GetEnvironmentVariable('PATH', 'User')
    } catch {
        Write-Warn "Refresh de PATH parcial. Continuando..."
    }

    $zanaCmd = Get-Command zana -ErrorAction SilentlyContinue
}

if ($zanaCmd) {
    Write-Ok "'zana' encontrado en: $($zanaCmd.Source)"
} else {
    Write-Warn "'zana' no encontrado en PATH de sesión actual."
    Write-Warn "Solución manual / Manual fix:"
    Write-Warn "  1. Cierra y abre una nueva terminal."
    Write-Warn "  2. Ejecuta: pipx ensurepath"
    Write-Warn "  3. Vuelve a abrir la terminal y prueba: zana --help"
}

# ─────────────────────────────────────────────────────────────
# PASO 8 — Lanzar `zana init`
# ─────────────────────────────────────────────────────────────

Write-Info "Inicializando ZANA..."

if (Get-Command zana -ErrorAction SilentlyContinue) {
    try {
        zana init
    } catch {
        Write-Warn "zana init reportó un error: $_"
    }
} else {
    Write-Warn "Ejecuta manualmente / Run manually: zana init"
}

# ─────────────────────────────────────────────────────────────
# PASO 9 — Mensaje final
# ─────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ZANA CLI instalada y lista / Installed & Ready  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host "  --> zana --help" -ForegroundColor Cyan
Write-Host "  --> zana chat" -ForegroundColor Cyan
Write-Host "  JUNTOS HACEMOS TEMBLAR LOS CIELOS." -ForegroundColor Magenta
Write-Host ""
