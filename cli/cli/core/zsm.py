"""
ZSM — ZANA Sovereign Machine.

The fallback cognitive engine when no LLM provider is configured.
ZANA does not fail without an LLM. It operates in sovereign mode:
using only its local substrate (vault, memory, skills, ledger).

Philosophy:
  An LLM amplifies reasoning. Without it, ZANA is still an agent —
  it can search, recall, execute skills, and log decisions.
  What it cannot do is generate novel language or synthesize across
  arbitrary domains. It tells the user this honestly, and shows them
  exactly what connecting an LLM would unlock.

This is not a degraded experience. It is a transparent one.
"""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel
from rich.text import Text

from cli.tui.theme import console

# ── Capability registry ────────────────────────────────────────────────────────

SOVEREIGN_CAPABILITIES = [
    ("zana memory search <query>", "Busca en tus memorias episódicas (SQLite local)"),
    ("zana vault search <query>", "Busca en tu vault de notas (FTS5 local)"),
    ("zana aeon status", "Muestra el estado y DNA de tu Aeón"),
    ("zana aeon card", "Genera tu tarjeta de identidad del Aeón"),
    ("zana aeon resonance", "Test de resonancia → calibra el arquetipo"),
    ("zana aeon habitat", "Tu Aeón en su mundo 2.5D"),
    ("zana sentinel report", "Civic Ledger — auditoría SHA-256 de decisiones"),
    ("zana skill list", "Lista tus skills procedurales activos"),
]

LLM_UNLOCKS = [
    ("Razonamiento natural", "Conversar, sintetizar, responder preguntas abiertas"),
    ("Síntesis de vault", "Citar y conectar tus notas automáticamente"),
    (
        "WisdomRules automáticas",
        "El Aeón genera reglas de sabiduría desde tus conversaciones",
    ),
    ("Skill Extraction", "Extraer skills de tus flujos de trabajo"),
    ("Analyst / Z-Think", "Razonamiento simbólico distribuido"),
]

PROVIDERS = {
    "Ollama (local, gratis, soberano)": "OLLAMA_BASE_URL=http://localhost:11434\nZANA_PRIMARY_MODEL=gemma3:4b",
    "Anthropic Claude": "ANTHROPIC_API_KEY=sk-ant-...\nZANA_PRIMARY_MODEL=claude-haiku-4-5-20251001",
    "Google Gemini": "GEMINI_API_KEY=AIza...\nZANA_PRIMARY_MODEL=gemini-2.0-flash",
    "OpenAI GPT": "OPENAI_API_KEY=sk-...\nZANA_PRIMARY_MODEL=gpt-4o-mini",
    "Groq (rápido)": "GROQ_API_KEY=gsk_...\nZANA_PRIMARY_MODEL=llama-3.1-8b-instant",
}


# ── Intent detection ───────────────────────────────────────────────────────────


def _detect_intent(query: str) -> str:
    """Map user input to the closest sovereign capability."""
    q = query.lower()

    if any(
        w in q
        for w in ["recuerda", "recuerdo", "ayer", "antes", "última", "pasada", "cuando"]
    ):
        return "memory"
    if any(w in q for w in ["nota", "vault", "archivo", "doc", "obsidian", "busca"]):
        return "vault"
    if any(w in q for w in ["skill", "habilidad", "workflow", "automatiza"]):
        return "skill"
    if any(w in q for w in ["aeon", "estado", "sigilo", "dna", "gen"]):
        return "aeon"
    if any(w in q for w in ["ledger", "audit", "decisión", "registro"]):
        return "ledger"
    return "general"


# ── ZSM response engine ────────────────────────────────────────────────────────


def respond(query: str) -> None:
    """Process a query in sovereign mode (no LLM)."""
    intent = _detect_intent(query)

    if intent == "memory":
        _respond_memory(query)
    elif intent == "vault":
        _respond_vault(query)
    elif intent == "skill":
        _respond_skill()
    elif intent == "aeon":
        _respond_aeon()
    elif intent == "ledger":
        _respond_ledger()
    else:
        _respond_general(query)


def _respond_memory(query: str) -> None:
    """Attempt episodic memory search, explain LLM gap."""
    db = Path.home() / ".zana" / "episodic.db"

    if db.exists():
        try:
            import sqlite3

            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memories")
            count = cur.fetchone()[0]
            conn.close()
            _sovereign_result(
                title="Memoria Episódica",
                body=f"Tienes {count:,} memorias almacenadas.\n\n"
                f"[dim]Ejecuta:[/dim] [cyan]zana memory search {query[:30]}[/cyan]\n"
                f"[dim]para buscar en ellas directamente.[/dim]",
            )
        except Exception:
            pass
    else:
        _sovereign_result(
            title="Memoria Episódica",
            body="Aún no tienes memorias almacenadas.\n\n"
            "[dim]Conecta un LLM para que el Aeón comience a recordar tus conversaciones.[/dim]",
        )
    _show_llm_unlock("WisdomRules automáticas")


def _respond_vault(query: str) -> None:
    """Search vault with FTS5."""
    vault_db = Path.home() / ".zana" / "vault.db"
    if not vault_db.exists():
        _sovereign_result(
            title="Vault",
            body="No hay vault indexado.\n\n[dim]Ejecuta:[/dim] [cyan]zana init[/cyan] [dim]para indexar tu conocimiento.[/dim]",
        )
        return

    try:
        from cli.core.vault.infrastructure.index.fts_index import FTSIndex

        fts = FTSIndex(vault_db)
        terms = " ".join(w for w in query.split() if len(w) > 2)
        results = fts.search(terms, limit=3)
        fts.close()

        if results:
            body = f"Encontré {len(results)} nota(s) relevante(s):\n\n"
            for r in results:
                body += f"[white]▷ {r['title']}[/white]\n"
                body += f"  [dim]{r['excerpt'][:80]}...[/dim]\n\n"
        else:
            body = f"Sin resultados para: [white]{terms}[/white]\n\n[dim]Prueba términos más simples.[/dim]"

        _sovereign_result(title="Búsqueda en Vault", body=body)
    except Exception as e:
        _sovereign_result(title="Vault", body=f"[dim]Error: {e}[/dim]")

    _show_llm_unlock("Síntesis de vault")


def _respond_skill() -> None:
    skills_path = Path.home() / ".zana" / "skills_registry.json"
    if skills_path.exists():
        import json

        try:
            data = json.loads(skills_path.read_text())
            skills = data.get("skills", [])
            body = f"{len(skills)} skill(s) registrado(s):\n\n"
            for s in skills[:5]:
                body += f"  ▷ [white]{s.get('name', '?')}[/white] — {s.get('description', '')[:50]}\n"
        except Exception:
            body = "Error leyendo el registro de skills."
    else:
        body = "No hay skills registrados. Ejecuta [cyan]zana skill create[/cyan]"
    _sovereign_result(title="Skills Procedurales", body=body)
    _show_llm_unlock("Skill Extraction")


def _respond_aeon() -> None:
    console.print(
        "[dim]→[/dim] Ejecuta [cyan]zana aeon status[/cyan] para ver tu Aeón completo."
    )


def _respond_ledger() -> None:
    ledger_path = Path.home() / ".zana" / "civic_ledger.jsonl"
    if ledger_path.exists():
        lines = ledger_path.read_text().strip().splitlines()
        _sovereign_result(
            title="Civic Ledger",
            body=f"{len(lines)} entradas registradas.\n\n[dim]Cada decisión de tu Aeón está firmada SHA-256 en tu disco.[/dim]",
        )
    else:
        _sovereign_result(
            title="Civic Ledger",
            body="El ledger se activa cuando el Aeón razona con un LLM.",
        )


def _respond_general(query: str) -> None:
    """Main ZSM response for general queries."""
    content = Text()
    content.append("Modo Soberano Básico activo.\n\n", style="bold magenta")
    content.append(
        "Sin un proveedor LLM configurado, no puedo generar razonamiento de lenguaje natural.\n"
        "Lo que sí puedo hacer ahora mismo:\n\n",
        style="dim",
    )
    for cmd, desc in SOVEREIGN_CAPABILITIES:
        content.append(f"  [cyan]{cmd}[/cyan]\n", style="")
        content.append(f"  {desc}\n\n", style="dim")

    content.append("\nLo que desbloquea un LLM:\n\n", style="bold white")
    for feature, desc in LLM_UNLOCKS:
        content.append(f"  [white]{feature}[/white]\n", style="")
        content.append(f"  {desc}\n\n", style="dim")

    content.append("\nConectar un proveedor (elige uno):\n\n", style="bold white")
    for provider, config in PROVIDERS.items():
        content.append(f"  [magenta]{provider}[/magenta]\n", style="")
        for line in config.splitlines():
            content.append(f"    [dim]echo '{line}' >> ~/.zana/.env[/dim]\n", style="")
        content.append("\n")

    content.append(
        "El más sencillo: instala Ollama → [cyan]ollama pull gemma3:4b[/cyan]\n"
        "Luego: [cyan]echo 'OLLAMA_BASE_URL=http://localhost:11434' >> ~/.zana/.env[/cyan]\n"
        "Reinicia: [cyan]zana chat[/cyan]\n\n",
        style="dim",
    )
    content.append(
        "La inteligencia de inferencia es el motor.\n"
        "Tu Aeón — memoria, skills, ledger, vault — es el alma.\n"
        "El alma ya existe. Añade el motor cuando quieras.",
        style="italic dim",
    )

    console.print(
        Panel(
            content,
            title="[bold magenta] ◈ ZANA MODO SOBERANO ◈ [/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def _sovereign_result(title: str, body: str) -> None:
    console.print(
        Panel(
            body,
            title=f"[bold magenta] ◈ {title} ◈ [/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def _show_llm_unlock(feature: str) -> None:
    desc = next((d for f, d in LLM_UNLOCKS if f == feature), "")
    console.print(
        f"\n[dim]◈ Con LLM: [white]{feature}[/white] — {desc}[/dim]\n"
        "[dim]  Ejecuta [cyan]zana init[/cyan] para configurar uno.[/dim]\n"
    )


# ── Provider detection ─────────────────────────────────────────────────────────


def has_llm_provider() -> bool:
    """Return True if at least one LLM provider is configured."""
    import os

    keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OLLAMA_BASE_URL",
    ]
    # Check env vars
    for k in keys:
        if os.environ.get(k, "").strip():
            return True
    # Check ~/.zana/.env
    env_file = Path.home() / ".zana" / ".env"
    if env_file.exists():
        content = env_file.read_text()
        for k in keys:
            if k in content:
                line = next((l for l in content.splitlines() if l.startswith(k)), "")  # noqa: E741
                val = line.split("=", 1)[-1].strip()
                if val and val not in (
                    "",
                    "your_key_here",
                    "sk-...",
                    "AIza...",
                    "gsk_...",
                ):
                    return True
    return False


def load_env_file() -> None:
    """Load ~/.zana/.env into os.environ if not already loaded."""
    import os

    env_file = Path.home() / ".zana" / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = val.strip()
