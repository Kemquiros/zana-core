"""
zana provider — manage LLM engines and active models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from zana.tui.theme import console

app = typer.Typer(
    name="provider",
    help="Manage LLM engines (OpenAI, Anthropic, Ollama, etc.) and active models.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

ZANA_ENV = Path.home() / ".zana" / ".env"


def _load_env() -> dict[str, str]:
    if not ZANA_ENV.exists():
        return {}
    env = {}
    for line in ZANA_ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _write_env(env: dict[str, str]) -> None:
    lines = []
    if ZANA_ENV.exists():
        # Preserving original file structure is complex, we overwrite for simplicity in this command
        pass
    for k, v in env.items():
        lines.append(f"{k}={v}")
    ZANA_ENV.write_text("\n".join(lines) + "\n")


@app.command("list")
def cmd_provider_list() -> None:
    """List configured providers and their active status."""
    env = _load_env()
    primary = env.get("ZANA_PRIMARY_PROVIDER", "zsm")
    model = env.get("ZANA_PRIMARY_MODEL", "sovereign")

    table = Table(title="Configured Providers", border_style="magenta")
    table.add_column("Provider", style="bold")
    table.add_column("Status", style="accent")
    table.add_column("Active Model", style="muted")

    providers = ["anthropic", "openai", "gemini", "groq", "openrouter", "ollama", "zsm"]
    keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "ollama": "OLLAMA_BASE_URL",
    }

    for p in providers:
        is_active = p == primary
        status = "[success]✓ Active[/success]" if is_active else ""
        if not status:
            key = keys.get(p)
            if key and env.get(key):
                status = "[muted]Configured[/muted]"
            elif p == "zsm":
                status = "[muted]Always available[/muted]"
            else:
                status = "[dim]Not set[/dim]"

        active_model = model if is_active else "—"
        table.add_row(p.capitalize(), status, active_model)

    console.print(table)


@app.command("use")
def cmd_provider_use(
    provider: Annotated[
        str, typer.Argument(help="Provider name (openai, anthropic, ollama, zsm, etc.)")
    ],
    model: Annotated[str | None, typer.Option("--model", "-m")] = None,
) -> None:
    """Switch the active provider and model."""
    provider = provider.lower()
    env = _load_env()

    keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "ollama": "OLLAMA_BASE_URL",
    }

    if provider != "zsm":
        key = keys.get(provider)
        if not key or not env.get(key):
            console.print(
                f"[error]Provider {provider} is not configured.[/error] Run [accent]zana setup[/accent] first."
            )
            return

    env["ZANA_PRIMARY_PROVIDER"] = provider
    if model:
        env["ZANA_PRIMARY_MODEL"] = model
    elif provider == "zsm":
        env["ZANA_PRIMARY_MODEL"] = "sovereign"

    _write_env(env)
    console.print(
        f"[success]✓ Switched to {provider.capitalize()}.[/success]"
        + (f" Model: [bold]{model}[/bold]" if model else "")
    )
