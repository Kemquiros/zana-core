import os
import json
from pathlib import Path
from dotenv import load_dotenv

import zana_steel_core
from mcp.server.fastmcp import FastMCP

# Load environment variables (from zana-core/.env)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Initialize MCP Server
mcp = FastMCP("zana-memory")

# Global instances (lazy load)
collection = None


def get_collection():
    global collection
    if collection is None:
        try:
            base_dir = Path(__file__).parent.parent.parent
            index_path = str(base_dir / "data" / "memory.index")
            collection = zana_steel_core.PyVectorIndex.load(index_path)
        except Exception:
            collection = zana_steel_core.PyVectorIndex()
    return collection


def format_chunks(results: list) -> str:
    """Format Zana Steel Core results into a readable string."""
    if not results:
        return "No relevant information found."

    formatted = []
    
    for item in results:
        # Depending on how pyo3 exposes the result, we try to access distance and metadata
        try:
            if isinstance(item, dict):
                dist = item.get("distance", 0.0)
                meta_str = item.get("metadata", "{}")
            else:
                dist = getattr(item, "distance", 0.0)
                meta_str = getattr(item, "metadata", "{}")
        except AttributeError:
            dist = item[1]
            meta_str = item[2]

        try:
            meta = json.loads(meta_str)
        except json.JSONDecodeError:
            meta = {}

        file_path = meta.get("file_path", "Unknown file")
        heading = meta.get("heading", "")
        heading_display = f" > {heading}" if heading else ""
        doc = meta.get("text", "")

        entry = f"--- Source: {file_path}{heading_display} (Distance: {dist:.4f}) ---\n{doc}\n"
        formatted.append(entry)

    return "\n".join(formatted)


@mcp.tool()
def semantic_search(query: str, collection_filter: str = None, top_k: int = 5) -> str:
    """
    Search the entire ZANA vault using semantic similarity.

    Args:
        query: The natural language search query.
        collection_filter: Optional string to filter by folder (e.g., 'entities', 'concepts', 'sources').
        top_k: Number of most relevant chunks to return (default: 5).

    Returns:
        Formatted text containing the most relevant chunks from the vault.
    """
    col = get_collection()
    query_embedding = zana_steel_core.embed_text(query, 384)

    fetch_k = top_k * 5 if collection_filter else top_k
    results = col.search(query_embedding, fetch_k)

    filtered_results = []
    for item in results:
        try:
            if isinstance(item, dict):
                meta_str = item.get("metadata", "{}")
            else:
                meta_str = getattr(item, "metadata", "{}")
        except AttributeError:
            meta_str = item[2]
            
        try:
            meta = json.loads(meta_str)
        except json.JSONDecodeError:
            meta = {}
            
        if collection_filter and meta.get("folder") != collection_filter:
            continue
            
        filtered_results.append(item)
        if len(filtered_results) >= top_k:
            break

    return format_chunks(filtered_results)


@mcp.tool()
def get_entity(name: str) -> str:
    """
    Retrieve the full context of a specific entity or concept by name.
    Useful for looking up people, projects, companies, or concepts.

    Args:
        name: The exact or partial name of the file/entity (e.g., 'VECANOVA', 'KoruOS').

    Returns:
        The content of the entity file.
    """
    # The Rust index may not have a `.get()` method. We can fall back to targeted semantic search.
    return semantic_search(f"Information about {name}", top_k=5)


@mcp.tool()
def related_concepts(entity_name: str, top_k: int = 3) -> str:
    """
    Find concepts and other entities related to a specific entity name via embeddings.

    Args:
        entity_name: The name of the entity to find relations for.
        top_k: Number of related concepts to return.

    Returns:
        Formatted text with related information.
    """
    return semantic_search(entity_name, top_k=top_k)


def main():
    mcp.run()


if __name__ == "__main__":
    main()