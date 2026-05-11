"""
Vault Cartographer — User-controlled discovery of knowledge sources.

The human decides where their knowledge lives.
ZANA is the map-maker, not the explorer.
"""

from __future__ import annotations

import os
from pathlib import Path

from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.text import Text

from zana.core.vault.domain.models import (
    SourceKind,
    VaultDocument,
    VaultIndex,
    VaultSource,
)
from zana.core.vault.infrastructure.index.fts_index import FTSIndex
from zana.core.vault.infrastructure.readers.markdown_reader import iter_documents
from zana.tui.theme import console

VAULT_DB_PATH = Path.home() / ".zana" / "vault.db"

# ── Source discovery ───────────────────────────────────────────────────────────


def _count_files(path: Path, extensions: set[str]) -> tuple[int, float]:
    """Count matching files and total size in MB."""
    count = 0
    size = 0
    try:
        for dirpath, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = Path(dirpath) / f
                if fp.suffix.lower() in extensions:
                    count += 1
                    try:  # noqa: SIM105
                        size += fp.stat().st_size
                    except Exception:
                        pass
    except PermissionError:
        pass
    return count, size / (1024 * 1024)


KNOWLEDGE_EXTS = {".md", ".txt", ".markdown", ".rst"}


def _detect_sources() -> list[VaultSource]:
    sources: list[VaultSource] = []
    home = Path.home()

    candidates = [
        # Obsidian vaults
        (home / "Obsidian", SourceKind.OBSIDIAN, "Obsidian vault"),
        (home / "Documents" / "Obsidian", SourceKind.OBSIDIAN, "Obsidian vault"),
        (home / "obsidian", SourceKind.OBSIDIAN, "Obsidian vault"),
        # Logseq
        (home / "Logseq", SourceKind.LOGSEQ, "Logseq vault"),
        (home / "logseq", SourceKind.LOGSEQ, "Logseq vault"),
        # Common note folders
        (home / "Documents" / "Notes", SourceKind.FOLDER, "Carpeta Notes"),
        (home / "Documents" / "ZANA_Vault", SourceKind.FOLDER, "ZANA Vault"),
        (home / "Notes", SourceKind.FOLDER, "Carpeta Notes"),
        (home / "Desktop", SourceKind.FOLDER, "Escritorio"),
    ]

    seen: set[Path] = set()
    for path, kind, label in candidates:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        count, size = _count_files(path, KNOWLEDGE_EXTS)
        if count == 0:
            continue
        # Skip Desktop if > 5000 files (not a note vault, likely clutter)
        if kind == SourceKind.FOLDER and path.name == "Desktop" and count > 500:
            continue
        sources.append(
            VaultSource(
                path=path,
                kind=kind,
                label=label,
                file_count=count,
                size_mb=size,
            )
        )

    return sources


# ── Interactive selection ──────────────────────────────────────────────────────


def _render_selection(sources: list[VaultSource], cursor: int, mode: str) -> Panel:
    content = Text()

    if mode == "sources" and sources:
        content.append("Selecciona tus fuentes de conocimiento:\n\n", style="dim")
        for i, src in enumerate(sources):
            is_cursor = i == cursor
            is_selected = src.selected

            prefix = "▸ " if is_cursor else "  "
            check = "[✓]" if is_selected else "[ ]"
            style = (
                "bold white" if is_cursor else ("dim" if not is_selected else "white")
            )

            line = f"{prefix}{check} {src.display}"
            content.append(line + "\n", style=style)

        content.append("\n[ ] Ruta personalizada...\n", style="dim")
        content.append(
            "[ ] Empezar vacío — el vault crece con conversaciones\n", style="dim"
        )
        content.append(
            "\n[dim]Espacio: seleccionar · Enter: continuar · ↑↓: mover[/dim]"
        )
    else:
        content.append("No encontré vaults existentes.\n\n", style="dim")
        content.append("Opciones:\n\n", style="dim")
        content.append("  [1] Ingresar ruta de carpeta\n", style="white")
        content.append(
            "  [2] Empezar vacío — el vault crece con conversaciones\n", style="white"
        )
        content.append("\n[dim]Elige 1 o 2:[/dim]")

    return Panel(
        content,
        title="[bold magenta] ◈ CARTOGRAFÍA DEL VAULT ◈ [/bold magenta]",
        border_style="magenta",
        padding=(1, 2),
    )


def run_vault_cartography() -> list[Path]:
    """
    Interactive vault discovery. Returns list of selected source paths.
    Returns empty list if user chooses to start empty.
    """
    sources = _detect_sources()

    if not sources:
        return _manual_selection()

    return _interactive_selection(sources)


def _manual_selection() -> list[Path]:
    console.print(
        Panel(
            "No encontré vaults existentes en las rutas comunes.\n\n"
            "  [1] Ingresar ruta de carpeta manualmente\n"
            "  [2] Empezar vacío — el vault crece con conversaciones\n\n"
            "[dim]Elige 1 o 2:[/dim]",
            title="[bold magenta] ◈ CARTOGRAFÍA DEL VAULT ◈ [/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    while True:
        choice = console.input("  → ").strip()
        if choice == "1":
            raw = console.input("  Ruta de la carpeta: ").strip()
            path = Path(raw).expanduser()
            if path.exists():
                return [path]
            console.print("  [dim]Ruta no encontrada. Empezando vacío.[/dim]")
            return []
        if choice == "2":
            return []


def _interactive_selection(sources: list[VaultSource]) -> list[Path]:
    """Simplified interactive selection without curses dependency."""
    console.print(
        Panel(
            "ZANA encontró estas fuentes de conocimiento en tu sistema:",
            title="[bold magenta] ◈ CARTOGRAFÍA DEL VAULT ◈ [/bold magenta]",
            border_style="magenta",
            padding=(0, 2),
        )
    )

    for i, src in enumerate(sources, 1):
        console.print(f"  [dim]{i}.[/dim] {src.display}")

    console.print()
    console.print(f"  [dim]{len(sources) + 1}.[/dim] Ingresar ruta personalizada")
    console.print(
        f"  [dim]{len(sources) + 2}.[/dim] Empezar vacío — el vault crece con conversaciones"
    )
    console.print()

    raw = console.input(
        f"  [dim]→[/dim] Elige fuentes [ej: 1,3 o {len(sources) + 1} o {len(sources) + 2}]: "
    ).strip()

    if not raw or raw == str(len(sources) + 2):
        return []

    if raw == str(len(sources) + 1):
        path_raw = console.input("  Ruta de la carpeta: ").strip()
        path = Path(path_raw).expanduser()
        if path.exists():
            return [path]
        console.print("  [dim]Ruta no encontrada. Empezando vacío.[/dim]")
        return []

    selected: list[Path] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(sources):
                selected.append(sources[idx].path)
        except ValueError:
            pass

    return selected


# ── Indexing ───────────────────────────────────────────────────────────────────


def index_sources(source_paths: list[Path]) -> VaultIndex:
    """Index all documents from selected sources. Returns VaultIndex."""
    if not source_paths:
        return VaultIndex(ready=True)

    all_docs: list[VaultDocument] = []
    for path in source_paths:
        console.print(f"  [dim]Leyendo {path}...[/dim]")
        docs = iter_documents(path)
        all_docs.extend(docs)

    if not all_docs:
        return VaultIndex(source_paths=source_paths, ready=True)

    fts = FTSIndex(VAULT_DB_PATH)

    indexed_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Indexando conocimiento...", total=len(all_docs))

        def _cb(current: int, total: int) -> None:
            nonlocal indexed_count
            indexed_count = current
            progress.update(task, completed=current)

        fts.index_documents(all_docs, progress_cb=_cb)

    total_docs = fts.total_docs()
    total_words = fts.total_words()

    console.print(
        f"\n  [bold green]✓[/bold green] [white]{total_docs:,} notas indexadas "
        f"· {total_words:,} palabras[/white]"
    )

    # The Memory Echo — the HOLY SHIT moment
    echo = fts.find_memory_echo()
    if echo:
        _show_memory_echo(echo)

    fts.close()

    return VaultIndex(
        source_paths=source_paths,
        total_docs=total_docs,
        total_words=total_words,
        db_path=VAULT_DB_PATH,
        ready=True,
    )


def _show_memory_echo(echo: dict) -> None:
    """The Memory Echo — shows the user a note from their past that resonates."""
    from datetime import datetime

    excerpt = echo.get("excerpt", "").strip()
    path = echo.get("path", "")
    modified_at = echo.get("modified_at", 0)

    if not excerpt:
        return

    try:
        date_str = datetime.fromtimestamp(modified_at).strftime("%d %b %Y")
    except Exception:
        date_str = "hace algún tiempo"

    short_path = Path(path).name if path else "nota desconocida"

    content = Text()
    content.append("Tu Aeón encontró algo.\n\n", style="dim magenta")
    content.append(f'"{excerpt}"\n\n', style="italic white")
    content.append(f"— {short_path}, {date_str}", style="dim")

    console.print()
    console.print(
        Panel(
            content,
            title="[bold magenta] ◈ ECO DE MEMORIA ◈ [/bold magenta]",
            border_style="magenta",
            padding=(1, 3),
        )
    )
    console.print("  [dim]Es exactamente para esto que fui construido.[/dim]\n")

    try:  # noqa: SIM105
        input("  [Enter para continuar]")
    except (EOFError, KeyboardInterrupt):
        pass


def search_vault(query: str, limit: int = 5) -> list[dict]:
    """Search the indexed vault. Used by the chat command."""
    if not VAULT_DB_PATH.exists():
        return []
    fts = FTSIndex(VAULT_DB_PATH)
    results = fts.search(query, limit=limit)
    fts.close()
    return results
