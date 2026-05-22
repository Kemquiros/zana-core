import asyncio
import json
import os
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
        try:
            from zana.core.memory_lite import get_db

            db = get_db()
            doc_id = db.add(fact, source="repl", collection="zana_vault")
            db.add_episodic("user", fact)
            db.close()
            console.print(
                f"[success]✓ Memory saved[/success] [muted](id:{doc_id})[/muted] — [muted]{fact[:80]}[/muted]"
            )
        except Exception as exc:
            console.print(f"[error]Memory write failed: {exc}[/error]")
        return True

    elif base_cmd == "/query":
        if len(cmd_parts) < 2:
            console.print('[warning]Usage: /query "<question>"[/warning]')
            return True
        q = " ".join(cmd_parts[1:])
        try:
            from zana.core.memory_lite import get_db

            db = get_db()
            results = db.search(q, collection="zana_vault", n=5)
            db.close()
            if results:
                console.print(
                    f"\n[secondary]Memory results for:[/secondary] [muted]{q}[/muted]\n"
                )
                for i, r in enumerate(results, 1):
                    excerpt = r["content"][:120].replace("\n", " ")
                    console.print(
                        f"  [accent]{i}.[/accent] [muted]({r['score']:.3f})[/muted] {excerpt}"
                    )
                console.print()
            else:
                console.print(f"[muted]No memories found for: {q}[/muted]")
        except Exception as exc:
            console.print(f"[error]Memory query failed: {exc}[/error]")
        return True

    elif base_cmd.startswith("/"):
        console.print(
            f"[warning]Unknown command: {base_cmd}. Type /help for available commands.[/warning]"
        )
        return True

    return False


_PLACEHOLDER_KEYS = {"your_key_here", "sk-...", "AIza...", "gsk_...", "sk-ant-...", ""}

_PROVIDER_MAP = [
    ("ANTHROPIC_API_KEY", "claude-3-5-haiku-20241022"),
    ("GEMINI_API_KEY", "gemini/gemini-2.0-flash"),
    ("OPENAI_API_KEY", "gpt-4o-mini"),
    ("GROQ_API_KEY", "groq/llama-3.3-70b-versatile"),
    ("OLLAMA_BASE_URL", "ollama/llama3"),
]

_MODEL_TO_KEY = {
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "gpt": "OPENAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "ollama": "OLLAMA_BASE_URL",
}


def _key_valid(env_var: str) -> bool:
    val = os.environ.get(env_var, "").strip()
    return bool(val) and val not in _PLACEHOLDER_KEYS


def _detect_model() -> str:
    """Pick model: validate ZANA_PRIMARY_MODEL against its provider key, fallback to first valid key."""
    primary = os.environ.get("ZANA_PRIMARY_MODEL", "").strip()
    if primary:
        # Derive which env var this model needs
        prefix = primary.split("/")[0].lower()
        required_key = _MODEL_TO_KEY.get(prefix)
        if required_key is None:
            # Unknown prefix — try model name prefix
            for pfx, key in _MODEL_TO_KEY.items():
                if primary.lower().startswith(pfx):
                    required_key = key
                    break
        if required_key and _key_valid(required_key):
            return primary
        # Primary model's key is missing/placeholder — fall through to auto-detect

    for env_var, model in _PROVIDER_MAP:
        if _key_valid(env_var):
            return model

    return "gpt-4o-mini"


async def _direct_llm_loop(session) -> None:
    """SPROUT tier: direct LiteLLM chat when gateway is offline but API key is configured."""
    from rich.panel import Panel

    try:
        import litellm

        litellm.suppress_debug_info = True
    except ImportError:
        console.print(
            "[error]litellm no instalado. Ejecuta: pip install 'vecanova-zana' --upgrade[/error]"
        )
        return

    model = _detect_model()

    console.print(
        Panel(
            f"[dim]Gateway no disponible en [white]ws://localhost:54446[/white].\n\n"
            f"Modo [bold green]SPROUT[/bold green] activo — conectando con [cyan]{model}[/cyan] directamente.\n"
            f"Memoria local · Ledger · Vault — disponibles.\n\n"
            f"[dim]Ejecuta [cyan]zana start[/cyan] para el Engine completo (Docker).[/dim]",
            title="[bold green] ◈ ZANA MODO SPROUT ◈ [/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print(
        "[primary]ZANA SPROUT activo. [accent]Ctrl+C[/accent] para salir.[/primary]\n"
    )

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are ZANA, a sovereign personal AI assistant. "
                "You run locally on the user's hardware. Be helpful, direct, and intelligent. "
                "Keep responses concise unless detail is explicitly requested."
            ),
        }
    ]

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

        messages.append({"role": "user", "content": user_input.strip()})

        try:
            from zana.core.memory_lite import get_db

            db = get_db()
            db.add_episodic("user", user_input.strip())
            db.close()
        except Exception:
            pass

        console.print("[secondary]ZANA>[/secondary] ", end="")

        try:
            response_text = ""
            stream = await litellm.acompletion(
                model=model,
                messages=messages,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    console.print(delta, end="")
                    response_text += delta
            console.print()

            messages.append({"role": "assistant", "content": response_text})

            try:
                from zana.core.memory_lite import get_db

                db = get_db()
                db.add_episodic("assistant", response_text)
                db.close()
            except Exception:
                pass

        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "quota" in exc_str or "rate" in exc_str:
                console.print(
                    f"\n[warning]Cuota agotada ({model}). Activa billing en tu proveedor "
                    f"o cambia de modelo con: [accent]zana setup[/accent][/warning]\n"
                )
            elif "401" in exc_str or "auth" in exc_str or "invalid" in exc_str:
                console.print(
                    f"\n[error]API key inválida para {model}. "
                    f"Verifica con: [accent]zana doctor[/accent][/error]\n"
                )
            else:
                console.print(f"\n[error]Error LLM ({model}): {exc}[/error]\n")
            messages.pop()


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

        from zana.core.zsm import load_env_file
        from zana.core.zsm import respond as zsm_respond

        load_env_file()

        from zana.core.tier import _has_llm_key

        if _has_llm_key():
            await _direct_llm_loop(session)
            return

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
