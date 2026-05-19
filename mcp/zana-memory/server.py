"""
ZANA Memory MCP Server — SPROUT-compatible.

Tier detection:
  GROVE+  → zana_steel_core (Rust, vector embeddings)
  SPROUT  → memory_lite (SQLite FTS5, zero deps)

Usage:
  python server.py                  # stdio transport (default, for Claude Code / Cline)
  ZANA_MCP_PORT=7340 python server.py  # SSE transport

Register in claude_desktop_config.json:
  { "zana": { "command": "python", "args": ["/path/to/server.py"] } }
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Make the CLI package importable when running from repo root
_cli_path = Path(__file__).parent.parent.parent / "cli"
if str(_cli_path) not in sys.path:
    sys.path.insert(0, str(_cli_path))

mcp = FastMCP("zana-memory")

# ---------------------------------------------------------------------------
# Backend selection — Rust vector index (GROVE+) or SQLite FTS5 (SPROUT)
# ---------------------------------------------------------------------------

_USE_RUST = False
_rust_collection = None


def _get_rust_collection():
    global _rust_collection
    if _rust_collection is None:
        try:
            import zana_steel_core

            base = Path(__file__).parent.parent.parent
            idx = str(base / "data" / "memory.index")
            try:
                _rust_collection = zana_steel_core.PyVectorIndex.load(idx)
            except Exception:
                _rust_collection = zana_steel_core.PyVectorIndex()
        except ImportError:
            pass
    return _rust_collection


def _detect_backend() -> str:
    try:
        import zana_steel_core as _  # noqa: F401

        return "rust"
    except ImportError:
        pass
    return "sprout"


_BACKEND = _detect_backend()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def semantic_search(query: str, collection: str = "zana_vault", top_k: int = 5) -> str:
    """Search ZANA memory using semantic similarity (or FTS5 in SPROUT mode).

    Args:
        query: Natural language search query.
        collection: Collection / namespace to search (default: zana_vault).
        top_k: Number of results to return (default: 5).

    Returns:
        Formatted ranked results with source and excerpt.
    """
    if _BACKEND == "rust":
        import json

        import zana_steel_core

        col = _get_rust_collection()
        emb = zana_steel_core.embed_text(query, 384)
        results = col.search(emb, top_k)
        lines = []
        for item in results:
            try:
                meta_str = (
                    item.get("metadata", "{}")
                    if isinstance(item, dict)
                    else getattr(item, "metadata", "{}")
                )
                dist = (
                    item.get("distance", 0.0)
                    if isinstance(item, dict)
                    else getattr(item, "distance", 0.0)
                )
            except AttributeError:
                dist, meta_str = item[1], item[2]
            try:
                meta = json.loads(meta_str)
            except Exception:
                meta = {}
            src = meta.get("file_path", "unknown")
            text = meta.get("text", "")
            lines.append(f"[{dist:.4f}] {src}\n{text[:300]}")
        return "\n---\n".join(lines) if lines else "No results found."

    # SPROUT — SQLite FTS5
    from zana.core.memory_lite import get_db

    db = get_db()
    results = db.search(query, collection=collection, n=top_k)
    db.close()
    if not results:
        return "No results found in local memory."
    lines = []
    for r in results:
        score = r.get("score", 0.0)
        src = r.get("source", "—")
        content = r.get("content", "")[:300]
        lines.append(f"[{score:.3f}] {src}\n{content}")
    return "\n---\n".join(lines)


@mcp.tool()
def memory_add(text: str, source: str = "mcp", collection: str = "zana_vault") -> str:
    """Add a document to ZANA's local SQLite FTS5 memory (SPROUT tier).

    Args:
        text: Content to store.
        source: Label identifying the origin (default: mcp).
        collection: Target collection (default: zana_vault).

    Returns:
        Confirmation with the assigned document ID.
    """
    from zana.core.memory_lite import get_db

    db = get_db()
    doc_id = db.add(text, source=source, collection=collection)
    db.close()
    return f"Stored in {collection} — id:{doc_id}  source:{source}"


@mcp.tool()
def get_entity(name: str) -> str:
    """Retrieve context about a specific entity, person, project, or concept.

    Args:
        name: Exact or partial name to look up (e.g. 'VECANOVA', 'KoruOS').

    Returns:
        Top matching entries from memory.
    """
    return semantic_search(f"Information about {name}", top_k=5)


@mcp.tool()
def related_concepts(entity_name: str, top_k: int = 3) -> str:
    """Find concepts and entities related to a given name.

    Args:
        entity_name: Entity to find relations for.
        top_k: Number of related entries to return.

    Returns:
        Formatted related entries.
    """
    return semantic_search(entity_name, top_k=top_k)


@mcp.tool()
def memory_stats() -> str:
    """Return stats about the ZANA local memory store.

    Returns:
        JSON-like summary of collections, record count, and DB size.
    """
    from zana.core.memory_lite import get_db

    db = get_db()
    stats = db.stats()
    db.close()
    backend = (
        "SQLite FTS5 (SPROUT)" if _BACKEND == "sprout" else "Rust vector index (GROVE+)"
    )
    return (
        f"Backend: {backend}\n"
        f"Total records: {stats['total']}\n"
        f"DB size: {stats['db_size_mb']} MB\n"
        f"Collections: {', '.join(stats['collections']) or 'none'}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    port = os.getenv("ZANA_MCP_PORT")
    if port:
        mcp.run(transport="sse", port=int(port))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
