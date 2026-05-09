import os

from rich.panel import Panel

from cli.tui.theme import console


def cmd_next() -> None:
    """Show the single next action to advance to the next tier."""
    from cli.core.i18n import t
    from cli.core.tier import (
        detect_tier,
        tier_label,
        tier_next_action,
        tier_progress_bar,
    )
    from cli.core.zsm import load_env_file

    load_env_file()
    tier = detect_tier()
    lang = os.environ.get("ZANA_LANG", "es")

    bar = tier_progress_bar(tier)
    label = tier_label(tier, lang)
    action = tier_next_action(tier, lang)

    console.print(
        Panel(
            f"  [{bar}] [bold white]{label}[/bold white]\n\n"
            f"  [accent]{action}[/accent]",
            title=f"[header] {t('tier.next_step_title', lang=lang).upper()} [/header]",
            border_style="magenta",
            padding=(1, 2),
        )
    )
