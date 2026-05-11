import sys

from rich.console import Console
from rich.theme import Theme

ZANA_THEME = Theme(
    {
        "primary": "bold magenta",
        "secondary": "bold violet",
        "accent": "bold bright_magenta",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "muted": "dim white",
        "header": "bold white on #3b0764",
        "code": "bright_cyan on #1e1b4b",
    }
)

# Detect if output is a TTY for automation-friendly (no color) output
is_interactive = sys.stdout.isatty()
console = Console(
    theme=ZANA_THEME, force_terminal=is_interactive, no_color=not is_interactive
)
if not is_interactive:
    # Disable decorative banners when not in a terminal
    BANNER = ""
    VALHALLA = ""
else:
    BANNER = """\
[primary]
                         ◆
                   ·  ·     ·  ·
               ·       ·   ·       ·
            ·       ·           ·       ·
           ·          ╭─────────╮          ·
          ·          ╱  ╭─────╮  ╲          ·
         ·          ╱  ╱  ╭─╮  ╲  ╲          ·
         ·    ◁────╱──╱──╱─╋─╲──╲──╲────▷    ·
         ·          ╲  ╲  ╰─╯  ╱  ╱          ·
          ·          ╲  ╰─────╯  ╱          ·
           ·          ╰─────────╯          ·
            ·       ·           ·       ·
               ·       ·   ·       ·
                   ·  ·     ·  ·
           ◆                           ◆

               [ Z · A · N · A ]
            SOVEREIGN  COGNITIVE  CORTEX[/primary]
"""

    VALHALLA = """\
[accent]
                       ▲
                      ███
                     █████
                    ███████
                   █████████
                  █████ █████
                 █████   █████
                █████     █████
               █████████████████
               ▀█████     █████▀
                 ▀█████ █████▀
                   ▀███████▀
                     ▀███▀
                       ▼

             [ V A L H A L L A   R E A C H E D ][/accent]
"""
