import asyncio
import json

import typer

from cli.tui.theme import console

GATEWAY_WS = "ws://localhost:54446/sense/stream"


async def _chat_loop() -> None:
    try:
        import websockets
    except ImportError:
        console.print(
            "[error]websockets package missing. Run: uv pip install websockets[/error]"
        )
        raise typer.Exit(1)

    console.print("[primary]ZANA Chat — type your message, Ctrl+C to exit[/primary]\n")

    try:
        async with websockets.connect(GATEWAY_WS) as ws:
            while True:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("[accent]You>[/accent] ")
                    )
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input.strip():
                    continue

                await ws.send(json.dumps({"type": "text", "content": user_input}))

                console.print("[secondary]ZANA>[/secondary] ", end="")
                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") == "chunk":
                        console.print(data.get("content", ""), end="")
                    elif data.get("type") == "end":
                        console.print()
                        break

    except OSError:
        console.print("[error]Cannot reach Gateway at ws://localhost:54446[/error]")
        console.print("[muted]Run `zana start` first.[/muted]")
        raise typer.Exit(1)


def cmd_chat() -> None:
    asyncio.run(_chat_loop())
