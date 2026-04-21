"""
zana memory — query and inspect ZANA's 4-store memory system.

  zana memory search <query>   semantic search via ChromaDB
  zana memory recall [n]       last N episodic records (PostgreSQL)
  zana memory stats            collection sizes across all stores
"""
import json
import os
from datetime import datetime

import httpx
from rich.table import Table
from rich.panel import Panel
from rich import box

from cli.tui.theme import console

CHROMA_URL = os.getenv("ZANA_CHROMA_URL", "http://localhost:58001")
GATEWAY_URL = f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}"


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
        payload = {"query_texts": [query_text], "n_results": n_results,
                   "include": ["documents", "distances", "metadatas"]}
        r = httpx.post(f"{CHROMA_URL}/api/v1/collections/{cid}/query",
                       json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def cmd_memory_search(query: str, collection: str = "zana_vault", n: int = 5) -> None:
    console.print(f"\n[primary]MEMORY SEARCH[/primary] [muted]→ \"{query}\"[/muted] "
                  f"[muted](collection: {collection}, top-{n})[/muted]\n")

    result = _chroma_query(collection, query, n)

    if result is None:
        console.print(f"[error]Collection '{collection}' not found.[/error]")
        cols = _chroma_collections()
        if cols:
            names = ", ".join(c["name"] for c in cols)
            console.print(f"[muted]Available: {names}[/muted]")
        else:
            console.print("[muted]ChromaDB offline or no collections. Run: zana embed[/muted]")
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

    table = Table(show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1))
    table.add_column("#",        style="muted",       width=3)
    table.add_column("Score",    style="accent",      width=7)
    table.add_column("Source",   style="bold white",  width=22)
    table.add_column("Excerpt",  style="white")

    for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas), 1):
        score = f"{1 - dist:.3f}" if dist is not None else "—"
        source = (meta or {}).get("source", "—")
        if len(source) > 22:
            source = "…" + source[-19:]
        excerpt = doc[:120].replace("\n", " ") + ("…" if len(doc) > 120 else "")
        table.add_row(str(i), score, source, excerpt)

    console.print(Panel(table, title=f"[header] Semantic Search Results [/header]",
                        border_style="magenta", padding=(0, 1)))


def cmd_memory_recall(n: int = 10) -> None:
    """Retrieve last N episodic memories via Gateway endpoint."""
    console.print(f"\n[primary]EPISODIC RECALL[/primary] [muted]— last {n} memories[/muted]\n")

    try:
        r = httpx.get(f"{GATEWAY_URL}/memory/episodic?limit={n}", timeout=5)
        r.raise_for_status()
        records = r.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[error]Gateway error {e.response.status_code}[/error]")
        return
    except Exception:
        console.print("[error]Gateway offline. Run: zana start[/error]")
        return

    if not records:
        console.print("[muted]No episodic records yet.[/muted]")
        return

    table = Table(show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1))
    table.add_column("When",    style="muted",       width=18)
    table.add_column("Role",    style="accent",      width=8)
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

    console.print(Panel(table, title="[header] Episodic Memory [/header]",
                        border_style="magenta", padding=(0, 1)))


def cmd_memory_stats() -> None:
    console.print("\n[primary]MEMORY STATS[/primary]\n")

    table = Table(show_header=True, header_style="header", box=box.ROUNDED, padding=(0, 1))
    table.add_column("Store",       style="bold white", width=16)
    table.add_column("Backend",     style="muted",      width=16)
    table.add_column("Collections", width=13)
    table.add_column("Records",     width=10)
    table.add_column("Status",      width=12)

    # ChromaDB
    cols = _chroma_collections()
    if cols is not None:
        total_docs = 0
        for c in cols:
            try:
                r = httpx.get(f"{CHROMA_URL}/api/v1/collections/{c['id']}/count", timeout=3)
                total_docs += r.json() if r.status_code == 200 else 0
            except Exception:
                pass
        table.add_row("Semantic", "ChromaDB", str(len(cols)), str(total_docs),
                      "[success]✓ Online[/success]")
    else:
        table.add_row("Semantic", "ChromaDB", "—", "—", "[error]✗ Offline[/error]")

    # Episodic via gateway
    try:
        r = httpx.get(f"{GATEWAY_URL}/memory/stats", timeout=3)
        stats = r.json() if r.status_code == 200 else {}
        ep_count = stats.get("episodic_count", "?")
        table.add_row("Episodic", "PostgreSQL+pgvector", "1", str(ep_count),
                      "[success]✓ Online[/success]")
    except Exception:
        table.add_row("Episodic", "PostgreSQL+pgvector", "—", "—", "[error]✗ Offline[/error]")

    table.add_row("World Model", "Neo4j", "—", "—", "[muted]via Gateway[/muted]")
    table.add_row("Procedural", "JSON files", "—", "—", "[success]✓ Local[/success]")

    console.print(Panel(table, title="[header] 4-Store Memory System [/header]",
                        border_style="magenta", padding=(0, 1)))
