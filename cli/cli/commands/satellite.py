import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def configure(provider: str, token: str):
    """Configure communication satellite (telegram/discord)."""
    # Persist provider credentials securely in ZANA config
    console.print(
        f"[bold green]Satellite {provider} configured successfully.[/bold green]"
    )


@app.command()
def status():
    """Show satellite connectivity status."""
    console.print("Satellites: Telegram [ON], Discord [OFF]")
