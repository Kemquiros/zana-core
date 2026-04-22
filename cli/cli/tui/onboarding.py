import shutil
import subprocess
from pathlib import Path

import questionary
from questionary import Style

from cli.tui.theme import console, BANNER

ZANA_CONFIG_DIR = Path.home() / ".config" / "zana"
ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"
ENV_EXAMPLE = Path(__file__).parent.parent.parent.parent / ".env.example"

Q_STYLE = Style(
    [
        ("qmark", "fg:#e879f9 bold"),
        ("question", "fg:#f0abfc bold"),
        ("answer", "fg:#c084fc bold"),
        ("pointer", "fg:#e879f9 bold"),
        ("highlighted", "fg:#f0abfc bg:#3b0764 bold"),
        ("selected", "fg:#c084fc"),
        ("separator", "fg:#6b21a8"),
        ("instruction", "fg:#a855f7 italic"),
        ("text", "fg:#f3e8ff"),
    ]
)


def _check_docker() -> bool:
    return shutil.which("docker") is not None and _docker_running()


def _docker_running() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_env() -> bool:
    return ENV_FILE.exists()


def _setup_api_keys() -> dict:
    console.print(
        "\n[secondary]Configure your LLM providers[/secondary] [muted](press Enter to skip)[/muted]\n"
    )

    keys = {}
    providers = [
        ("ANTHROPIC_API_KEY", "Anthropic API key (Claude)"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("GEMINI_API_KEY", "Gemini API key"),
        ("GROQ_API_KEY", "Groq API key"),
        ("OPENROUTER_API_KEY", "OpenRouter API key"),
    ]

    for env_var, label in providers:
        val = questionary.password(f"  {label}:", style=Q_STYLE).ask()
        if val and val.strip():
            keys[env_var] = val.strip()

    return keys


def _write_env(keys: dict) -> None:
    if ENV_EXAMPLE.exists():
        template = ENV_EXAMPLE.read_text()
    else:
        template = ""

    lines = template.splitlines()
    out_lines = []
    written = set()

    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            var = line.split("=", 1)[0].strip()
            if var in keys:
                out_lines.append(f"{var}={keys[var]}")
                written.add(var)
                continue
        out_lines.append(line)

    for var, val in keys.items():
        if var not in written:
            out_lines.append(f"{var}={val}")

    ENV_FILE.write_text("\n".join(out_lines) + "\n")


def run_onboarding() -> bool:
    """First-run wizard. Returns True if setup completed successfully."""
    console.print(BANNER)
    console.print("[primary]ZANA en línea. Sensores activos.[/primary]\n")

    issues = []

    # Docker check
    if not _check_docker():
        console.print("[warning]  Docker not found or not running.[/warning]")
        console.print(
            "  Install Docker: [code]https://docs.docker.com/get-docker/[/code]\n"
        )
        issues.append("docker")
    else:
        console.print("[success]  Docker detected.[/success]")

    # .env check
    if not _check_env():
        console.print("[warning]  No .env file found.[/warning]")
        setup = questionary.confirm(
            "  Configure API keys now?", default=True, style=Q_STYLE
        ).ask()

        if setup:
            keys = _setup_api_keys()
            if keys:
                _write_env(keys)
                console.print("[success]  .env created.[/success]")
            else:
                console.print(
                    "[muted]  Skipped — you can run `zana login` later.[/muted]"
                )
    else:
        console.print("[success]  .env found.[/success]")

    ZANA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (ZANA_CONFIG_DIR / ".onboarded").touch()

    if issues:
        console.print(
            f"\n[warning]Setup incomplete: {', '.join(issues)} need attention.[/warning]"
        )
        console.print("[muted]Run `zana doctor` after resolving dependencies.[/muted]")
        return False

    console.print(
        "\n[success]ZANA ready. Run `zana start` to boot the stack.[/success]"
    )
    return True


def is_first_run() -> bool:
    return not (ZANA_CONFIG_DIR / ".onboarded").exists()
