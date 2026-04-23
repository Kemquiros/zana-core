import asyncio
import json
import os
import shlex
import typer

from cli.tui.theme import console

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
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
        console.print("  [accent]/memory[/accent] - Save a memory (e.g. /memory \"Max is my dog\")")
        console.print("  [accent]/query[/accent]  - Query the memory bank (e.g. /query \"What is AGI?\")")
        console.print("  [accent]/exit[/accent]   - Exit the REPL\n")
        return True
        
    elif base_cmd == "/clear":
        console.clear()
        return True
        
    elif base_cmd == "/memory":
        if len(cmd_parts) < 2:
            console.print("[warning]Usage: /memory \"<fact>\"[/warning]")
            return True
        fact = " ".join(cmd_parts[1:])
        console.print(f"[success]Memory injected to the Episodic Store:[/success] [muted]{fact}[/muted]")
        # TODO: send special memory payload to websocket or invoke memory module
        return True
        
    elif base_cmd == "/query":
        if len(cmd_parts) < 2:
            console.print("[warning]Usage: /query \"<question>\"[/warning]")
            return True
        q = " ".join(cmd_parts[1:])
        console.print(f"[secondary]Searching Z-Network for:[/secondary] [muted]{q}[/muted]")
        # TODO: Send query payload
        return True

    elif base_cmd.startswith("/"):
        console.print(f"[warning]Unknown command: {base_cmd}. Type /help for available commands.[/warning]")
        return True

    return False

async def _chat_loop() -> None:
    try:
        import websockets
    except ImportError:
        console.print(
            "[error]websockets package missing. Run: uv pip install websockets[/error]"
        )
        raise typer.Exit(1)

    console.print(
        "\n[primary]ZANA REPL activo. Escribe un mensaje o usa [accent]/help[/accent] para ver comandos. [accent]Ctrl+C[/accent] para salir.[/primary]\n"
    )

    history_file = os.path.expanduser("~/.zana/.chat_history")
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    if PromptSession is not None:
        style = Style.from_dict({
            'prompt': 'ansimagenta bold',
            'input': 'ansiwhite',
        })
        session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            style=style
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
                    console.print("\n[muted]Saliendo del Córtex. Hasta la próxima, John.[/muted]")
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
        console.print("[error]No se pudo conectar al ZANA Gateway (ws://localhost:54446).[/error]")
        console.print("[muted]Asegúrate de ejecutar `zana start` primero para iniciar el contenedor del Engine.[/muted]")
        
        # If in debug or simulation mode, let's still run the REPL without the websocket for testing the UI
        if os.getenv("ZANA_DEBUG_REPL") == "1":
            console.print("[warning]ZANA_DEBUG_REPL activo. Corriendo en modo offline (Mock).[/warning]")
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
                    console.print("\n[muted]Saliendo del Córtex. Hasta la próxima, John.[/muted]")
                    break

                if not user_input.strip():
                    continue
                if _handle_slash_command(user_input.strip()):
                    continue
                    
                console.print(f"[secondary]ZANA (Mock)>[/secondary] Entendido. (Recibí: {user_input})")
        else:
            raise typer.Exit(1)


def cmd_chat() -> None:
    asyncio.run(_chat_loop())
