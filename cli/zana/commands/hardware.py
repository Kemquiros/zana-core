"""
hardware.py — Real hardware detection and Ollama model recommendations.
Part of ZANA v3.1.1 Sprint 5.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

from rich import box
from rich.panel import Panel
from rich.table import Table

from zana.tui.theme import console

# ---------------------------------------------------------------------------
# Model catalog — hardcoded, ordered by quality desc within each tier
# ---------------------------------------------------------------------------

MODELS = [
    # ≥ 32 GB tier
    {
        "name": "Llama 3.3 70B",
        "params": "70B",
        "ram_min_gb": 32,
        "speed_cpu": "3–6",
        "desc": "Flagship open model, best reasoning",
    },
    {
        "name": "Qwen2.5 72B",
        "params": "72B",
        "ram_min_gb": 36,
        "speed_cpu": "2–5",
        "desc": "Multilingual powerhouse",
    },
    {
        "name": "Mixtral 8x22B",
        "params": "141B MoE",
        "ram_min_gb": 48,
        "speed_cpu": "1–3",
        "desc": "Sparse MoE, excellent for long context",
    },
    # 16–31 GB tier
    {
        "name": "Llama 3.1 70B (Q4)",
        "params": "70B Q4",
        "ram_min_gb": 16,
        "speed_cpu": "4–8",
        "desc": "70B quantized, great quality/size ratio",
    },
    {
        "name": "Qwen2.5 14B",
        "params": "14B",
        "ram_min_gb": 10,
        "speed_cpu": "8–14",
        "desc": "Strong multilingual, code, math",
    },
    {
        "name": "Mixtral 8x7B",
        "params": "47B MoE",
        "ram_min_gb": 26,
        "speed_cpu": "4–7",
        "desc": "MoE efficiency with large model quality",
    },
    # 8–15 GB tier
    {
        "name": "Llama 3.1 8B",
        "params": "8B",
        "ram_min_gb": 8,
        "speed_cpu": "12–25",
        "desc": "Best 8B class, instruction-tuned",
    },
    {
        "name": "Mistral 7B",
        "params": "7B",
        "ram_min_gb": 6,
        "speed_cpu": "15–28",
        "desc": "Fast, capable, widely supported",
    },
    {
        "name": "Qwen2.5 7B",
        "params": "7B",
        "ram_min_gb": 6,
        "speed_cpu": "14–26",
        "desc": "Multilingual, code, strong reasoning",
    },
    # 4–7 GB tier
    {
        "name": "Phi-3 Mini 3.8B",
        "params": "3.8B",
        "ram_min_gb": 4,
        "speed_cpu": "25–45",
        "desc": "Microsoft small model, punches above weight",
    },
    {
        "name": "Llama 3.2 3B",
        "params": "3B",
        "ram_min_gb": 4,
        "speed_cpu": "28–50",
        "desc": "Meta's compact, solid for general use",
    },
    {
        "name": "Gemma2 2B",
        "params": "2B",
        "ram_min_gb": 3,
        "speed_cpu": "35–60",
        "desc": "Google small, good quality/speed balance",
    },
    # < 4 GB tier
    {
        "name": "TinyLlama 1.1B",
        "params": "1.1B",
        "ram_min_gb": 2,
        "speed_cpu": "50–80",
        "desc": "Minimal resources, basic tasks",
    },
    {
        "name": "Qwen2 0.5B",
        "params": "0.5B",
        "ram_min_gb": 1,
        "speed_cpu": "80–150",
        "desc": "Ultra-lightweight, triage/edge use",
    },
]


# ---------------------------------------------------------------------------
# Hardware detection helpers
# ---------------------------------------------------------------------------


def _get_ram_gb() -> float | None:
    """Detect total RAM in GB using only stdlib."""
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(re.search(r"(\d+)", line).group(1))
                        return round(kb / 1024 / 1024, 1)
        elif system == "Darwin":
            result = subprocess.run(
                ["sysctl", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                match = re.search(r"(\d+)", result.stdout)
                if match:
                    return round(int(match.group(1)) / 1024 / 1024 / 1024, 1)
        elif system == "Windows":
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.isdigit():
                        return round(int(line) / 1024 / 1024 / 1024, 1)
    except Exception:
        pass
    return None


def _get_cpu() -> str:
    """Return CPU brand string."""
    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    cpu = platform.processor()
    return cpu if cpu else "Unknown CPU"


def _get_gpu_info() -> str:
    """Best-effort GPU/VRAM detection."""
    system = platform.system()
    machine = platform.machine()

    # Apple Silicon — unified memory, no discrete GPU needed
    if system == "Darwin" and machine == "arm64":
        return "Apple Silicon (unified memory)"

    # NVIDIA via nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = [
                    line.strip()
                    for line in result.stdout.strip().splitlines()
                    if line.strip()
                ]
                gpus = []
                for line in lines:
                    parts = line.split(",")
                    if len(parts) == 2:
                        name = parts[0].strip()
                        vram_mib = parts[1].strip()
                        try:
                            vram_gb = round(int(vram_mib) / 1024, 1)
                            gpus.append(f"{name} ({vram_gb} GB VRAM)")
                        except ValueError:
                            gpus.append(name)
                    else:
                        gpus.append(line)
                return " · ".join(gpus)
        except Exception:
            pass

    return "GPU no detectada / CPU inference"


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------


def _rank_models(ram_gb: float, top: int):
    """Return top-N models sorted: fitting first (best quality), then by RAM desc."""

    def fit_key(m):
        ram_min = m["ram_min_gb"]
        if ram_gb >= ram_min:
            return (0, -ram_min)  # fits — higher ram_min = better model first
        elif ram_gb >= ram_min * 0.8:
            return (1, -ram_min)  # tight
        else:
            return (2, -ram_min)  # doesn't fit

    sorted_models = sorted(MODELS, key=fit_key)
    return sorted_models[:top]


def _fit_label(ram_gb: float, ram_min: int) -> str:
    """Return Rich-formatted fit label."""
    if ram_gb >= ram_min:
        return "[success]✓ Encaja[/success]"
    elif ram_gb >= ram_min * 0.8:
        return "[warning]⚠ Justo[/warning]"
    else:
        return "[error]✗ No alcanza[/error]"


# ---------------------------------------------------------------------------
# Panel builders
# ---------------------------------------------------------------------------


def _build_hardware_panel(ram_gb: float | None, cpu: str, gpu: str) -> Panel:
    table = Table(
        box=box.ROUNDED,
        border_style="magenta",
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Campo", style="primary", min_width=14)
    table.add_column("Valor", style="accent")

    table.add_row("OS", f"{platform.system()} {platform.release()}")
    table.add_row("Arquitectura", platform.machine())
    table.add_row("CPU", cpu)
    table.add_row("Núcleos", str(os.cpu_count() or "?"))
    ram_str = f"{ram_gb} GB" if ram_gb is not None else "[error]No detectada[/error]"
    table.add_row("RAM total", ram_str)
    table.add_row("GPU / VRAM", gpu)

    return Panel(
        table, title="[primary]Hardware detectado[/primary]", border_style="magenta"
    )


def _build_recommendations_panel(models, ram_gb: float, top: int) -> Panel:
    table = Table(
        box=box.ROUNDED,
        border_style="magenta",
        show_header=True,
        header_style="primary",
        padding=(0, 1),
    )
    table.add_column("Rank", style="muted", width=5)
    table.add_column("Modelo", style="accent")
    table.add_column("Params", style="muted", width=10)
    table.add_column("RAM req", style="muted", width=8)
    table.add_column("Vel. CPU (tok/s)", style="muted", width=16)
    table.add_column("Fit", width=14)
    table.add_column("Descripción", style="muted")

    for i, m in enumerate(models, start=1):
        fit = _fit_label(ram_gb, m["ram_min_gb"])
        table.add_row(
            str(i),
            m["name"],
            m["params"],
            f"≥ {m['ram_min_gb']} GB",
            m["speed_cpu"],
            fit,
            m["desc"],
        )

    return Panel(
        table,
        title=f"[primary]Recomendaciones Ollama — top {top}[/primary]",
        border_style="magenta",
    )


def _build_next_step_panel(ram_gb: float | None) -> Panel:
    lines = []

    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_ollama = bool(os.environ.get("OLLAMA_BASE_URL"))

    if has_anthropic:
        lines.append(
            "[success]✓ Claude disponible — no necesitas modelos locales[/success]"
        )
    if has_ollama:
        lines.append("[success]✓ Ollama configurado[/success]")

    if not has_anthropic and not has_ollama:
        lines.append(
            "[accent]→ Instala Ollama: https://ollama.com · Luego: ollama pull llama3.1:8b[/accent]"
        )

    # Suggest best fitting model if no Ollama configured
    if not has_ollama and ram_gb is not None:
        fitting = [m for m in MODELS if ram_gb >= m["ram_min_gb"]]
        if fitting:
            best = fitting[0]
            pull_name = best["name"].lower().replace(" ", "").replace("(q4)", ":q4_K_M")
            # Simplify pull name for ollama
            pull_map = {
                "llamia3.370b": "llama3.3:70b",
                "llama3.170b(q4)": "llama3.1:70b-instruct-q4_K_M",
                "llama3.18b": "llama3.1:8b",
                "llama3.23b": "llama3.2:3b",
                "mistral7b": "mistral:7b",
                "qwen2.572b": "qwen2.5:72b",
                "qwen2.514b": "qwen2.5:14b",
                "qwen2.57b": "qwen2.5:7b",
                "qwen20.5b": "qwen2:0.5b",
                "mixtral8x7b": "mixtral:8x7b",
                "mixtral8x22b": "mixtral:8x22b",
                "phi-3mini3.8b": "phi3:mini",
                "gemma22b": "gemma2:2b",
                "tinyllama1.1b": "tinyllama",
                "llama3.370b": "llama3.3:70b",
            }
            simplified = best["name"].lower().replace(" ", "").replace("(q4)", "")
            pull_name = pull_map.get(simplified, simplified)
            lines.append(
                f"[muted]Mejor modelo para tu RAM: [/muted][accent]{best['name']}[/accent]"
                f"[muted] → [/muted][accent]ollama pull {pull_name}[/accent]"
            )

    content = (
        "\n".join(lines) if lines else "[muted]Sin configuración detectada.[/muted]"
    )
    return Panel(
        content, title="[primary]Siguiente paso[/primary]", border_style="magenta"
    )


# ---------------------------------------------------------------------------
# llmfit integration (optional, --install flag)
# ---------------------------------------------------------------------------


def _try_llmfit_enrich(ram_gb: float | None):
    """Attempt to use llmfit if available; returns enriched lines or None."""
    try:
        import importlib.util

        spec = importlib.util.find_spec("llmfit")
        if spec is None:
            return None
        import llmfit  # type: ignore

        if hasattr(llmfit, "recommend"):
            return llmfit.recommend(ram_gb=ram_gb)
    except Exception:
        pass
    return None


def _install_llmfit():
    """Try to pip-install llmfit quietly."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "llmfit", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


def cmd_hardware(install: bool = False, recommend: bool = False, top: int = 5) -> None:
    """Detect hardware and recommend Ollama models for this machine."""

    # --- Detect ---
    ram_gb = _get_ram_gb()
    cpu = _get_cpu()
    gpu = _get_gpu_info()

    # Panel 1: always shown
    console.print(_build_hardware_panel(ram_gb, cpu, gpu))

    effective_ram = ram_gb if ram_gb is not None else 0.0

    # --- llmfit enrichment (--install) ---
    llmfit_lines = None
    if install:
        with console.status("[accent]Buscando llmfit...[/accent]"):
            llmfit_lines = _try_llmfit_enrich(effective_ram)
            if llmfit_lines is None:
                console.print("[muted]Instalando llmfit...[/muted]")
                ok = _install_llmfit()
                if ok:
                    llmfit_lines = _try_llmfit_enrich(effective_ram)
                if llmfit_lines is None:
                    console.print(
                        "[warning]llmfit no disponible — usando recomendaciones integradas.[/warning]"
                    )

    # Panel 2: recommendations
    if recommend or install:
        models = _rank_models(effective_ram, top)
        console.print(_build_recommendations_panel(models, effective_ram, top))
    else:
        # No flags: show top 3 fitting models
        models = _rank_models(effective_ram, 3)
        console.print(_build_recommendations_panel(models, effective_ram, 3))

    # Panel 3: next step
    console.print(_build_next_step_panel(ram_gb))
