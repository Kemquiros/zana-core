"""
zana hardware — Hardware analysis and LLM fit recommendations via llmfit.

llmfit is an open-source Rust tool that scans your CPU, RAM, and GPU and
scores ~106 LLM models across quality, speed, context, and hardware fit.
It recommends the highest-quality quantization that actually runs on your
machine — no guessing, no OOM crashes.

  GitHub : https://github.com/AlexsJones/llmfit
  Site   : https://llmfit.org
  License: MIT
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from cli.tui.theme import console


# ── helpers ───────────────────────────────────────────────────────────────

def _find_llmfit() -> str | None:
    found = shutil.which("llmfit")
    if found:
        return found
    cargo_bin = Path.home() / ".cargo" / "bin" / "llmfit"
    return str(cargo_bin) if cargo_bin.exists() else None


def _install_llmfit() -> bool:
    console.print("\n  [muted]Descargando llmfit (~5 MB)...[/muted]")
    r = subprocess.run(
        "curl -fsSL https://llmfit.org/install.sh | sh",
        shell=True,
    )
    if r.returncode == 0:
        cargo_bin = Path.home() / ".cargo" / "bin"
        os.environ["PATH"] = f"{cargo_bin}:{os.environ.get('PATH', '')}"
        return True
    if shutil.which("brew"):
        r = subprocess.run(["brew", "install", "llmfit"])
        return r.returncode == 0
    return False


def _run_llmfit(binary: str, *args: str, timeout: int = 15) -> dict | list | None:
    """Run llmfit with --json and parse output. Returns None on failure."""
    try:
        r = subprocess.run(
            [binary, *args, "--json"],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def _fmt_gb(val) -> str:
    if val is None:
        return "?"
    try:
        return f"{float(val):.1f} GB"
    except (TypeError, ValueError):
        return str(val)


# ── main command ──────────────────────────────────────────────────────────

def cmd_hardware(install: bool, recommend: bool, top: int) -> None:
    console.print()
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print("[bold white]  ZANA Hardware Intelligence — powered by llmfit[/bold white]")
    console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
    console.print(
        "\n  [accent]llmfit[/accent] escanea tu CPU, RAM y GPU y puntúa ~106 modelos LLM\n"
        "  según calidad, velocidad y ajuste a tu hardware exacto.\n"
        "  Recomienda la quantización más alta que tu máquina puede correr\n"
        "  sin quedarse sin memoria — sin adivinar, sin crashes.\n"
    )
    console.print(
        "  [muted]GitHub: https://github.com/AlexsJones/llmfit  ·  MIT License[/muted]\n"
    )

    binary = _find_llmfit()

    if not binary:
        console.print("  [yellow]⚠  llmfit no está instalado en este sistema.[/yellow]\n")

        if install:
            console.print("  Instalando llmfit...")
            if _install_llmfit():
                binary = _find_llmfit()
                if binary:
                    console.print("  [success]✅ llmfit instalado correctamente.[/success]\n")
                else:
                    console.print("  [error]Instalación completó pero el binario no se encontró en PATH.[/error]")
                    console.print("  [muted]Prueba: source ~/.bashrc && zana hardware[/muted]")
                    return
            else:
                console.print("  [error]No se pudo instalar automáticamente.[/error]")
                _print_manual_install()
                return
        else:
            console.print("  Para instalar ejecuta:")
            console.print("  [accent]  zana hardware --install[/accent]\n")
            console.print("  O manualmente:")
            _print_manual_install()
            return

    console.print(f"  [success]✅ llmfit encontrado:[/success] [muted]{binary}[/muted]\n")

    # ── Hardware summary ──────────────────────────────────────────────────
    console.print("[bold cyan]  ╔══ Tu Hardware ══════════════════════════════╗[/bold cyan]")
    hw = _run_llmfit(binary, "system")
    if hw and isinstance(hw, dict):
        ram  = _fmt_gb(hw.get("total_memory_gb") or hw.get("ram_gb") or hw.get("memory"))
        gpu  = hw.get("gpu_name") or hw.get("gpu") or hw.get("accelerator", "No detectada")
        vram = _fmt_gb(hw.get("vram_gb") or hw.get("gpu_memory_gb"))
        cpus = hw.get("cpu_cores") or hw.get("cpus") or "?"
        console.print(f"  [bold cyan]  ║[/bold cyan]  RAM  : [bold]{ram}[/bold]")
        console.print(f"  [bold cyan]  ║[/bold cyan]  GPU  : [bold]{gpu}[/bold]" + (f" · VRAM {vram}" if vram != "?" else ""))
        console.print(f"  [bold cyan]  ║[/bold cyan]  CPU  : [bold]{cpus} cores[/bold]")
    else:
        # Fallback: run without --json for human-readable output
        r = subprocess.run([binary, "system"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines()[:6]:
            if line.strip():
                console.print(f"  [bold cyan]  ║[/bold cyan]  {line.strip()}")
    console.print("[bold cyan]  ╚═════════════════════════════════════════════╝[/bold cyan]\n")

    if not recommend:
        console.print("  [muted]Añade [accent]--recommend[/accent] para ver los modelos recomendados para tu hardware.[/muted]\n")
        return

    # ── Model recommendations ─────────────────────────────────────────────
    console.print(f"[bold cyan]  ╔══ Top {top} Modelos para tu Hardware ══════════╗[/bold cyan]")

    # Try recommend subcommand, then fit as fallback
    data = _run_llmfit(binary, "recommend") or _run_llmfit(binary, "fit")

    models: list[dict] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                models.append({"name": item})
            elif isinstance(item, dict):
                models.append(item)
    elif isinstance(data, dict):
        raw = data.get("models") or data.get("recommendations") or []
        models = [{"name": m} if isinstance(m, str) else m for m in raw]

    if not models:
        # Fallback: run without --json and show raw output
        console.print("[bold cyan]  ║[/bold cyan]")
        r = subprocess.run([binary, "recommend"], capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines()[:top + 4]:
            if line.strip():
                console.print(f"  [bold cyan]  ║[/bold cyan]  {line.strip()}")
    else:
        console.print("[bold cyan]  ║[/bold cyan]")
        for i, m in enumerate(models[:top], 1):
            name    = m.get("name") or m.get("model") or m.get("id") or "?"
            quality = m.get("quality") or m.get("score") or ""
            speed   = m.get("speed") or m.get("tokens_per_second") or ""
            fit     = m.get("fit") or m.get("rating") or ""

            badge = ""
            if fit:
                badge = f" [success][{fit}][/success]"
            elif quality:
                badge = f" [muted](Q: {quality})[/muted]"

            speed_str = f"  [muted]~{speed} tok/s[/muted]" if speed else ""
            console.print(f"  [bold cyan]  ║[/bold cyan]  [bold]{i:2}.[/bold] [accent]{name}[/accent]{badge}{speed_str}")

    console.print("[bold cyan]  ║[/bold cyan]")
    console.print(f"[bold cyan]  ╚═════════════════════════════════════════════╝[/bold cyan]")
    console.print()
    console.print(
        "  [muted]Para usar el modelo recomendado con ZANA:[/muted]\n"
        "  [muted]1.[/muted] [accent]ollama pull <modelo>[/accent]\n"
        "  [muted]2.[/muted] [accent]zana setup[/accent] [muted]→ selecciónalo en el paso 2[/muted]\n"
        "  [muted]   o edita directamente:[/muted] [accent]ZANA_PRIMARY_MODEL=ollama/<modelo>[/accent] [muted]en ~/.zana/.env[/muted]\n"
    )


def _print_manual_install() -> None:
    console.print("\n  [muted]Instalación manual:[/muted]")
    console.print("  [bold]Linux / WSL:[/bold]   [accent]curl -fsSL https://llmfit.org/install.sh | sh[/accent]")
    console.print("  [bold]macOS:[/bold]          [accent]brew install llmfit[/accent]")
    console.print("  [bold]Windows:[/bold]        [accent]scoop install llmfit[/accent]")
    console.print("  [bold]Cargo:[/bold]          [accent]cargo install llmfit[/accent]")
    console.print("  [muted]  Luego ejecuta: zana hardware --recommend[/muted]\n")
