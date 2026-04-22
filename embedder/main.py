"""ZANA Vault Embedding Pipeline"""

import os
import sys
from pathlib import Path

import chromadb
import click
from rich.console import Console
from rich.progress import track
from sentence_transformers import SentenceTransformer

from chunker import chunk_file
from config import (
    CHROMA_HOST,
    CHROMA_PORT,
    COLLECTION_NAME,
    EMBED_MODEL,
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    SKIP_EXTENSIONS,
    SKIP_FOLDERS,
    VAULT_PATH,
)

console = Console()


def is_ignored(path: Path, vault_root: Path) -> bool:
    """Check if the file or any of its parent folders should be skipped."""
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True

    try:
        rel_path = path.relative_to(vault_root)
        for part in rel_path.parts:
            if part in SKIP_FOLDERS or part.startswith("."):
                return True
    except ValueError:
        pass

    return False


def get_vault_files(vault_root: Path) -> list[Path]:
    """Get all markdown files in the vault, excluding ignored ones."""
    files = []
    for root, dirs, filenames in os.walk(vault_root):
        # Mutate dirs in-place to skip ignored folders
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS and not d.startswith(".")]

        for name in filenames:
            file_path = Path(root) / name
            if file_path.suffix.lower() == ".md" and not is_ignored(
                file_path, vault_root
            ):
                files.append(file_path)

    return files


def split_long_chunk(text: str, max_chars: int) -> list[str]:
    """Split a very long chunk into smaller pieces."""
    if len(text) <= max_chars:
        return [text]

    # Simple semantic split (by paragraphs)
    pieces = []
    paragraphs = text.split("\n\n")
    current_piece = ""

    for p in paragraphs:
        if len(current_piece) + len(p) + 2 <= max_chars:
            current_piece += p + "\n\n"
        else:
            if current_piece:
                pieces.append(current_piece.strip())

            # If a single paragraph is longer than max_chars, split by sentences
            if len(p) > max_chars:
                sentences = p.split(". ")
                sub_piece = ""
                for s in sentences:
                    if len(sub_piece) + len(s) + 2 <= max_chars:
                        sub_piece += s + ". "
                    else:
                        if sub_piece:
                            pieces.append(sub_piece.strip())
                        sub_piece = s + ". "
                if sub_piece:
                    pieces.append(sub_piece.strip())
                current_piece = ""
            else:
                current_piece = p + "\n\n"

    if current_piece:
        pieces.append(current_piece.strip())

    return pieces


@click.command()
@click.option("--reset", is_flag=True, help="Reset the collection before embedding")
def cli(reset: bool):
    """Embed the entire Obsidian vault into ChromaDB."""
    console.print("[bold blue]ZANA Embedding Pipeline[/bold blue]")
    console.print(f"Vault: [green]{VAULT_PATH}[/green]")
    console.print(f"Chroma: [green]{CHROMA_HOST}:{CHROMA_PORT}[/green]")
    console.print(f"Model: [green]{EMBED_MODEL}[/green]")

    if not VAULT_PATH.exists():
        console.print(
            f"[bold red]Error:[/bold red] Vault path {VAULT_PATH} does not exist."
        )
        sys.exit(1)

    # Initialize ChromaDB client
    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # Check connection
        chroma_client.heartbeat()
    except Exception as e:
        console.print(f"[bold red]Error connecting to ChromaDB:[/bold red] {e}")
        console.print("Make sure the ChromaDB Docker container is running.")
        sys.exit(1)

    if reset:
        console.print("[yellow]Resetting collection...[/yellow]")
        try:
            chroma_client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass  # Collection does not exist

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    # Initialize Embedding Model
    console.print("[yellow]Loading embedding model...[/yellow]")
    model = SentenceTransformer(EMBED_MODEL, device="cpu")

    # Scan Vault
    console.print("[yellow]Scanning vault for markdown files...[/yellow]")
    files = get_vault_files(VAULT_PATH)
    console.print(f"Found [bold green]{len(files)}[/bold green] markdown files.")

    if not files:
        console.print("No files to embed. Exiting.")
        sys.exit(0)

    # Process and chunk files
    all_chunks = []

    for file_path in track(files, description="Chunking files..."):
        file_chunks = chunk_file(file_path, VAULT_PATH, min_chars=MIN_CHUNK_CHARS)

        for chunk in file_chunks:
            # Handle chunks that are too long
            if len(chunk.text) > MAX_CHUNK_CHARS:
                sub_texts = split_long_chunk(chunk.text, MAX_CHUNK_CHARS)
                for i, sub_text in enumerate(sub_texts):
                    # Create a new chunk object based on the original, with updated text and id
                    sub_chunk = chunk.__class__(
                        doc_id=f"{chunk.doc_id}_{i}",
                        text=sub_text,
                        heading=chunk.heading,
                        file_path=chunk.file_path,
                        file_name=chunk.file_name,
                        folder=chunk.folder,
                        subfolder=chunk.subfolder,
                        fm=chunk.fm,
                    )
                    all_chunks.append(sub_chunk)
            else:
                all_chunks.append(chunk)

    console.print(f"Generated [bold green]{len(all_chunks)}[/bold green] total chunks.")

    if not all_chunks:
        console.print("No valid chunks found. Exiting.")
        sys.exit(0)

    # Embed and upsert in batches
    batch_size = 100

    ids = []
    documents = []
    metadatas = []

    for chunk in all_chunks:
        ids.append(chunk.doc_id)
        # We embed a combination of the heading and the text for better context
        embed_text = f"{chunk.heading}\n\n{chunk.text}" if chunk.heading else chunk.text
        documents.append(embed_text)

        # Flatten metadata for ChromaDB
        meta = {
            "file_path": chunk.file_path,
            "file_name": chunk.file_name,
            "folder": chunk.folder,
            "subfolder": chunk.subfolder,
            "heading": chunk.heading,
        }
        # Add frontmatter, ensuring string values
        for k, v in chunk.fm.items():
            meta[f"fm_{k}"] = str(v)

        metadatas.append(meta)

    console.print(
        f"[yellow]Embedding and upserting {len(documents)} chunks to ChromaDB...[/yellow]"
    )

    # Process in batches to avoid memory issues and API limits
    for i in track(range(0, len(documents), batch_size), description="Upserting..."):
        batch_docs = documents[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]

        # Generate embeddings
        embeddings = model.encode(batch_docs).tolist()

        # Upsert to ChromaDB
        collection.upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_docs,
            metadatas=batch_metas,
        )

    console.print(
        "[bold green]✅ Embedding pipeline completed successfully![/bold green]"
    )


if __name__ == "__main__":
    cli()
