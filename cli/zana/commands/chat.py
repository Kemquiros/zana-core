import asyncio
import json
import shlex
from pathlib import Path

import typer
from rich.table import Table

from zana.tui.theme import console

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.styles import Style
except ImportError:
    PromptSession = None

GATEWAY_WS = "ws://localhost:54446/sense/stream"


def _handle_slash_command(command: str) -> bool:
    """Handles special slash commands. Returns True if handled, False if it's a normal message."""
    cmd_parts = shlex.split(command)
    base_cmd = cmd_parts[0].lower()

    if base_cmd in ["/exit", "/quit", "/q"]:
        raise EOFError()

    elif base_cmd == "/help":
        console.print("\n[secondary]ZANA REPL Commands:[/secondary]")
        console.print("  [accent]/help[/accent]   - Show this help message")
        console.print("  [accent]/clear[/accent]  - Clear the terminal screen")
        console.print(
            '  [accent]/memory[/accent] - Save a memory (e.g. /memory "Max is my dog")'
        )
        console.print(
            '  [accent]/query[/accent]  - Query the memory bank (e.g. /query "What is AGI?")'
        )
        console.print("  [accent]/exit[/accent]   - Exit the REPL\n")
        return True

    elif base_cmd == "/clear":
        console.clear()
        return True

    elif base_cmd == "/memory":
        if len(cmd_parts) < 2:
            console.print('[warning]Usage: /memory "<fact>"[/warning]')
            return True
        fact = " ".join(cmd_parts[1:])
        console.print(
            f"[success]Memory injected to the Episodic Store:[/success] [muted]{fact}[/muted]"
        )
        # TODO: send special memory payload to websocket or invoke memory module
        return True

    elif base_cmd == "/query":
        if len(cmd_parts) < 2:
            console.print('[warning]Usage: /query "<question>"[/warning]')
            return True
        q = " ".join(cmd_parts[1:])
        console.print(
            f"[secondary]Searching Z-Network for:[/secondary] [muted]{q}[/muted]"
        )
        # TODO: Send query payload
        return True

    elif base_cmd.startswith("/"):
        console.print(
            f"[warning]Unknown command: {base_cmd}. Type /help for available commands.[/warning]"
        )
        return True

    return False


async def _chat_loop() -> None:
    try:
        import websockets
    except ImportError:
        console.print(
            "[error]websockets package missing. Run: uv pip install websockets[/error]"
        )
        raise typer.Exit(1)  # noqa: B904

    console.print(
        "\n[primary]ZANA REPL activo. Escribe un mensaje o usa [accent]/help[/accent] para ver comandos. [accent]Ctrl+C[/accent] para salir.[/primary]\n"
    )

    history_file = Path.home() / ".zana" / ".chat_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    if PromptSession is not None:
        style = Style.from_dict(
            {
                "prompt": "ansimagenta bold",
                "input": "ansiwhite",
            }
        )
        session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            style=style,
        )
    else:
        session = None

    try:
        async with websockets.connect(GATEWAY_WS) as ws:
            while True:
                try:
                    if session:
                        user_input = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: session.prompt("You> ")
                        )
                    else:
                        user_input = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input("You> ")
                        )
                except (EOFError, KeyboardInterrupt):
                    console.print(
                        "\n[muted]Saliendo del Córtex. Hasta la próxima, John.[/muted]"
                    )
                    break

                if not user_input.strip():
                    continue

                if _handle_slash_command(user_input.strip()):
                    continue

                # Send normal message to ZANA
                await ws.send(json.dumps({"type": "text", "content": user_input}))

                console.print("[secondary]ZANA>[/secondary] ", end="")
                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") == "chunk":
                        # Print chunks as they come
                        console.print(data.get("content", ""), end="")
                    elif data.get("type") == "end":
                        console.print()
                        break
                    elif data.get("type") == "error":
                        console.print(f"\n[error]Error: {data.get('content')}[/error]")
                        break

    except OSError:
        from rich.panel import Panel

        from zana.core.zsm import respond as zsm_respond

        console.print(
            Panel(
                "[dim]Gateway no disponible en [white]ws://localhost:54446[/white].\n\n"
                "Activando [bold magenta]Modo Soberano (ZSM)[/bold magenta] — sin LLM, sin red.\n"
                "Memoria local · Skills · Ledger · Vault — todo disponible.\n\n"
                "[dim]Ejecuta [cyan]zana start[/cyan] para conectar el Engine completo.[/dim]",
                title="[bold magenta] ◈ ZANA MODO SOBERANO ◈ [/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )
        )

        _cap_table = Table(
            show_header=True,
            header_style="bold magenta",
            border_style="dim magenta",
            padding=(0, 1),
            expand=False,
        )
        _cap_table.add_column("Capacidad", style="bold bright_magenta", no_wrap=True)
        _cap_table.add_column("Ejemplo de uso", style="dim white")
        _cap_table.add_row("🤝  Compañía", "hola, cómo estás")
        _cap_table.add_row("🔢  Matemáticas", "calcula 15% de 340")
        _cap_table.add_row("⏰  Recordatorios", "recuérdame llamar a mamá mañana")
        _cap_table.add_row("💰  Economía", "gasté $45 en mercado")
        _cap_table.add_row("🌍  Idiomas", "traduce hello al francés")
        _cap_table.add_row("🧠  Memoria sesión", "qué recuerdas de antes")
        _cap_table.add_row("📂  Vault / Notas", "busca nota sobre proyecto")
        _cap_table.add_row("🍳  Recetas", "receta con pollo y arroz")
        _cap_table.add_row("🕐  Hora y fecha", "qué hora es / qué día es hoy")
        _cap_table.add_row("✨  Tu Aeon", "muéstrame mi Aeon / dna")
        _cap_table.add_row("📊  Nivel actual", "qué nivel tengo / siguiente nivel")
        _cap_table.add_row("🔐  Civic Ledger", "muestra el audit / ledger")
        _cap_table.add_row("⚙️  Skills", "qué habilidades tienes")
        _cap_table.add_row("💬  Chat general", "cualquier pregunta libre")
        console.print(_cap_table)

        console.print(
            "\n[primary]ZANA Soberano activo. Prueba: [accent]calcula 15% de 340[/accent]"
            " o [accent]recuérdame estudiar mañana[/accent] · [muted][accent]/help[/accent]"
            " para comandos · [accent]Ctrl+C[/accent] para salir[/muted][/primary]\n"
        )

        while True:
            try:
                if session:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: session.prompt("You> ")
                    )
                else:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("You> ")
                    )
            except (EOFError, KeyboardInterrupt):
                console.print(
                    "\n[muted]Saliendo del Córtex Soberano. Hasta la próxima.[/muted]"
                )
                break

            if not user_input.strip():
                continue
            if _handle_slash_command(user_input.strip()):
                continue

            console.print("[secondary]ZANA (Soberano)>[/secondary]")
            zsm_respond(user_input.strip())


def cmd_chat() -> None:
    asyncio.run(_chat_loop())
