"""
zana memory — query and inspect ZANA's 4-store memory system.

  zana memory search <query>   semantic search via ChromaDB
  zana memory recall [n]       last N episodic records (PostgreSQL)
  zana memory stats            collection sizes across all stores
"""

import os
from datetime import datetime

import httpx
from rich import box
from rich.panel import Panel
from rich.table import Table

from zana.tui.theme import console

CHROMA_URL = os.getenv("ZANA_CHROMA_URL", "http://localhost:58001")
GATEWAY_URL = f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}"


def _is_chroma_online() -> bool:
    """Return True if ChromaDB heartbeat responds within 2 seconds."""
    try:
        httpx.get(f"{CHROMA_URL}/api/v1/heartbeat", timeout=2).raise_for_status()
        return True
    except Exception:
        return False


def _chroma_collections() -> list[dict]:
    try:
        r = httpx.get(f"{CHROMA_URL}/api/v1/collections", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _chroma_query(collection: str, query_text: str, n_results: int = 5) -> dict | None:
    try:
        # Get collection id
        cols = _chroma_collections()
        col = next((c for c in cols if c["name"] == collection), None)
        if not col:
            return None
        cid = col["id"]
        payload = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "distances", "metadatas"],
        }
        r = httpx.post(
            f"{CHROMA_URL}/api/v1/collections/{cid}/query", json=payload, timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def cmd_memory_add(
    text: str,
    source: str = "cli",
    collection: str = "zana_vault",
    tag: str | None = None,
) -> None:
    """Add a document to SQLite FTS5 memory (SPROUT tier — no Docker required)."""
    console.print("\n[primary]MEMORY ADD[/primary]\n")

    metadata: dict = {}
    if tag:
        metadata["tag"] = tag

    from zana.core.memory_lite import get_db

    db = get_db()
    doc_id = db.add(text, source=source, collection=collection, metadata=metadata)
    db.close()

    console.print(
        Panel(
            f"[success]✓ Guardado[/success]  ID: [accent]{doc_id}[/accent]\n"
            f"[muted]Colección:[/muted] {collection}   [muted]Fuente:[/muted] {source}"
            + (f"   [muted]Tag:[/muted] {tag}" if tag else ""),
            title="[header] SQLite FTS5 — Modo Soberano [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def cmd_memory_search(query: str, collection: str = "zana_vault", n: int = 5) -> None:
    console.print(
        f'\n[primary]MEMORY SEARCH[/primary] [muted]→ "{query}"[/muted] '
        f"[muted](collection: {collection}, top-{n})[/muted]\n"
    )

    # ------------------------------------------------------------------
    # SPROUT fallback: ChromaDB offline → SQLite FTS5
    # ------------------------------------------------------------------
    if not _is_chroma_online():
        console.print(
            "[muted]ChromaDB offline — usando SQLite FTS5 (Modo Soberano)[/muted]\n"
        )
        from zana.core.memory_lite import get_db

        db = get_db()
        results = db.search(query, collection=collection, n=n)
        db.close()

        if not results:
            console.print(
                "[muted]Sin resultados en memoria local. "
                "Añade documentos con: zana embed[/muted]"
            )
            return

        table = Table(
            show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1)
        )
        table.add_column("#", style="muted", width=3)
        table.add_column("Score", style="accent", width=7)
        table.add_column("Source", style="bold white", width=22)
        table.add_column("Excerpt", style="white")

        for i, result in enumerate(results, 1):
            score = f"{result['score']:.3f}"
            source = result["source"]
            if len(source) > 22:
                source = "…" + source[-19:]
            content = result["content"]
            excerpt = content[:120].replace("\n", " ") + (
                "…" if len(content) > 120 else ""
            )
            table.add_row(str(i), score, source, excerpt)

        console.print(
            Panel(
                table,
                title="[header] Semantic Search Results [/header]",
                border_style="magenta",
                padding=(0, 1),
            )
        )
        return

    # ------------------------------------------------------------------
    # ChromaDB path (online)
    # ------------------------------------------------------------------
    result = _chroma_query(collection, query, n)

    if result is None:
        console.print(f"[error]Collection '{collection}' not found.[/error]")
        cols = _chroma_collections()
        if cols:
            names = ", ".join(c["name"] for c in cols)
            console.print(f"[muted]Available: {names}[/muted]")
        else:
            console.print(
                "[muted]ChromaDB offline or no collections. Run: zana embed[/muted]"
            )
        return

    if "error" in result:
        console.print(f"[error]Search failed: {result['error']}[/error]")
        return

    docs = result.get("documents", [[]])[0]
    dists = result.get("distances", [[]])[0]
    metas = result.get("metadatas", [[]])[0]

    if not docs:
        console.print("[muted]No results found.[/muted]")
        return

    table = Table(
        show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1)
    )
    table.add_column("#", style="muted", width=3)
    table.add_column("Score", style="accent", width=7)
    table.add_column("Source", style="bold white", width=22)
    table.add_column("Excerpt", style="white")

    for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas), 1):  # noqa: B905
        score = f"{1 - dist:.3f}" if dist is not None else "—"
        source = (meta or {}).get("source", "—")
        if len(source) > 22:
            source = "…" + source[-19:]
        excerpt = doc[:120].replace("\n", " ") + ("…" if len(doc) > 120 else "")
        table.add_row(str(i), score, source, excerpt)

    console.print(
        Panel(
            table,
            title="[header] Semantic Search Results [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def cmd_memory_recall(n: int = 10) -> None:
    """Retrieve last N episodic memories via Gateway, or SQLite FTS5 fallback."""
    console.print(
        f"\n[primary]EPISODIC RECALL[/primary] [muted]— last {n} memories[/muted]\n"
    )

    records: list[dict] = []
    gateway_ok = False

    try:
        r = httpx.get(f"{GATEWAY_URL}/memory/episodic?limit={n}", timeout=5)
        r.raise_for_status()
        records = r.json()
        gateway_ok = True
    except httpx.HTTPStatusError as e:
        console.print(f"[error]Gateway error {e.response.status_code}[/error]")
    except Exception:
        pass  # fall through to SQLite fallback below

    if not gateway_ok:
        console.print(
            "[muted]Gateway offline — usando SQLite FTS5 (Modo Soberano)[/muted]\n"
        )
        from zana.core.memory_lite import get_db

        db = get_db()
        lite_records = db.recall(n)
        db.close()

        # Normalise field names to match the Gateway shape consumed below
        records = [
            {
                "timestamp": rec["created_at"],
                "role": rec["source"],
                "content": rec["content"],
            }
            for rec in lite_records
        ]

    if not records:
        console.print("[muted]No episodic records yet.[/muted]")
        return

    table = Table(
        show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1)
    )
    table.add_column("When", style="muted", width=18)
    table.add_column("Role", style="accent", width=8)
    table.add_column("Summary", style="white")

    for rec in records:
        ts = rec.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            ts = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        role = rec.get("role", "—")
        summary = rec.get("content", "")[:100].replace("\n", " ")
        table.add_row(ts, role, summary)

    console.print(
        Panel(
            table,
            title="[header] Episodic Memory [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def cmd_memory_delete(doc_id: int) -> None:
    """Delete a single document by ID."""
    console.print(f"\n[primary]MEMORY DELETE[/primary] [muted]id={doc_id}[/muted]\n")
    from zana.core.memory_lite import get_db

    db = get_db()
    deleted = db.delete(doc_id)
    db.close()

    if deleted:
        console.print(f"[success]✓ Documento {doc_id} eliminado.[/success]")
    else:
        console.print(f"[error]✗ No existe ningún documento con id={doc_id}.[/error]")


def cmd_memory_clear(collection: str | None = None) -> None:
    """Delete all documents — optionally scoped to one collection."""
    target = f"colección '{collection}'" if collection else "TODAS las colecciones"
    console.print(f"\n[primary]MEMORY CLEAR[/primary] [muted]→ {target}[/muted]\n")

    from zana.core.memory_lite import get_db

    db = get_db()
    count = db.clear(collection=collection)
    db.close()

    console.print(f"[success]✓ {count} documentos eliminados de {target}.[/success]")


def cmd_memory_export(
    collection: str | None = None,
    fmt: str = "json",
    output: str | None = None,
) -> None:
    """Export SQLite FTS5 memory to JSON or CSV."""
    import csv
    import json as _json
    import sys

    console.print(f"\n[primary]MEMORY EXPORT[/primary] [muted]format={fmt}[/muted]\n")

    from zana.core.memory_lite import get_db

    db = get_db()
    docs = db.export_docs(collection=collection)
    db.close()

    if not docs:
        console.print("[muted]Sin documentos para exportar.[/muted]")
        return

    dest = open(output, "w", encoding="utf-8") if output else sys.stdout  # noqa: SIM115

    if fmt == "csv":
        writer = csv.DictWriter(
            dest,
            fieldnames=[
                "id",
                "collection",
                "source",
                "content",
                "metadata",
                "created_at",
            ],
        )
        writer.writeheader()
        for doc in docs:
            doc["metadata"] = _json.dumps(doc["metadata"], ensure_ascii=False)
            writer.writerow(doc)
    else:
        _json.dump(docs, dest, ensure_ascii=False, indent=2)
        dest.write("\n")

    if output:
        dest.close()
        console.print(
            f"[success]✓ {len(docs)} documentos exportados → {output}[/success]"
        )
    else:
        console.print(f"\n[muted]— {len(docs)} documentos —[/muted]")


def cmd_memory_import(path: str) -> None:
    """Import documents from a JSON file into SQLite FTS5 memory."""
    import json as _json

    console.print(f"\n[primary]MEMORY IMPORT[/primary] [muted]{path}[/muted]\n")

    from zana.core.memory_lite import get_db

    try:
        with open(path, encoding="utf-8") as f:
            docs = _json.load(f)
    except FileNotFoundError:
        console.print(f"[error]✗ Archivo no encontrado: {path}[/error]")
        return
    except _json.JSONDecodeError as e:
        console.print(f"[error]✗ JSON inválido: {e}[/error]")
        return

    if not isinstance(docs, list):
        console.print(
            "[error]✗ El archivo debe contener una lista JSON de documentos.[/error]"
        )
        return

    db = get_db()
    inserted = db.import_docs(docs)
    db.close()

    console.print(f"[success]✓ {inserted} documentos importados.[/success]")


def cmd_memory_stats() -> None:
    console.print("\n[primary]MEMORY STATS[/primary]\n")

    table = Table(
        show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1)
    )
    table.add_column("Store", style="bold white", width=16)
    table.add_column("Backend", style="muted", width=18)
    table.add_column("Collections", width=13)
    table.add_column("Records", width=10)
    table.add_column("Status", width=16)

    # ChromaDB
    chroma_online = _is_chroma_online()
    if chroma_online:
        cols = _chroma_collections()
        total_docs = 0
        for c in cols:
            try:
                r = httpx.get(
                    f"{CHROMA_URL}/api/v1/collections/{c['id']}/count", timeout=3
                )
                total_docs += r.json() if r.status_code == 200 else 0
            except Exception:
                pass
        table.add_row(
            "Semantic",
            "ChromaDB",
            str(len(cols)),
            str(total_docs),
            "[success]✓ Online[/success]",
        )
    else:
        table.add_row("Semantic", "ChromaDB", "—", "—", "[muted]✗ Offline[/muted]")

    # Episodic via gateway
    try:
        r = httpx.get(f"{GATEWAY_URL}/memory/stats", timeout=3)
        stats = r.json() if r.status_code == 200 else {}
        ep_count = stats.get("episodic_count", "?")
        table.add_row(
            "Episodic",
            "PostgreSQL+pgvector",
            "1",
            str(ep_count),
            "[success]✓ Online[/success]",
        )
    except Exception:
        table.add_row(
            "Episodic", "PostgreSQL+pgvector", "—", "—", "[muted]✗ Offline[/muted]"
        )

    table.add_row("World Model", "Neo4j", "—", "—", "[muted]via Gateway[/muted]")
    table.add_row("Procedural", "JSON files", "—", "—", "[success]✓ Local[/success]")

    # SQLite FTS5 — always available (SPROUT tier, no external deps)
    from zana.core.memory_lite import get_db

    try:
        db = get_db()
        lite_stats = db.stats()
        db.close()
        col_count = str(len(lite_stats["collections"]))
        rec_count = str(lite_stats["total"])
        size_label = f"{lite_stats['db_size_mb']} MB"
        table.add_row(
            "SQLite FTS5",
            f"SQLite ({size_label})",
            col_count,
            rec_count,
            "[success]✓ Local[/success]",
        )
    except Exception as exc:
        table.add_row("SQLite FTS5", "SQLite", "—", "—", f"[error]✗ {exc}[/error]")

    console.print(
        Panel(
            table,
            title="[header] 4-Store Memory System [/header]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
