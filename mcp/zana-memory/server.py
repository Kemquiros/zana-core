import os
from pathlib import Path
from dotenv import load_dotenv

import chromadb
from sentence_transformers import SentenceTransformer
from mcp.server.fastmcp import FastMCP

# Load environment variables (from zana-core/.env)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION_NAME = "vault_knowledge"
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# Initialize MCP Server
mcp = FastMCP("zana-memory")

# Global instances (lazy load)
chroma_client = None
collection = None
model = None


def get_chroma():
    global chroma_client, collection
    if chroma_client is None:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return collection


def get_model():
    global model
    if model is None:
        model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return model


def format_chunks(results: dict) -> str:
    """Format ChromaDB results into a readable string."""
    if not results or not results.get("documents") or not results["documents"][0]:
        return "No relevant information found."

    formatted = []
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0] if "distances" in results else [0] * len(docs)

    for doc, meta, dist in zip(docs, metas, distances):
        file_path = meta.get("file_path", "Unknown file")
        heading = meta.get("heading", "")
        heading_display = f" > {heading}" if heading else ""

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
    col = get_chroma()
    mod = get_model()

    query_embedding = mod.encode(query).tolist()

    where_clause = None
    if collection_filter:
        where_clause = {"folder": collection_filter}

    results = col.query(
        query_embeddings=[query_embedding], n_results=top_k, where=where_clause
    )

    return format_chunks(results)


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
    col = get_chroma()

    # Try exact match first
    results = col.get(where={"file_name": name})

    if results and results.get("documents"):
        # Reconstruct file from chunks
        docs = results["documents"]
        # Sort chunks by doc_id to keep order (crude sorting by chunk index)
        # Note: Doc IDs look like relative/path.md::chunk_N or relative/path.md::chunk_N_0
        combined = "\n\n".join(docs)
        return f"--- Entity: {name} ---\n{combined}"

    # If not exact match, do a targeted semantic search
    return semantic_search(f"Information about {name}", top_k=3)


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
