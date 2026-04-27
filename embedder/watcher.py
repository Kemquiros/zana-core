import sys
import time
import json
from pathlib import Path

import zana_steel_core
import click
from rich.console import Console
from sentence_transformers import SentenceTransformer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_file
from config import (
    MEMORY_INDEX_PATH,
    COLLECTION_NAME,
    EMBED_MODEL,
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    VAULT_PATH,
)
from main import is_ignored, split_long_chunk

console = Console()


class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, index, model):
        super().__init__()
        self.index = index
        self.model = model

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(Path(event.src_path), "created")

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(Path(event.src_path), "modified")

    def on_moved(self, event):
        if not event.is_directory:
            # Handle the deletion of the old path
            self.remove_file(Path(event.src_path))
            # Process the new path
            self.process_file(Path(event.dest_path), "moved")

    def on_deleted(self, event):
        if not event.is_directory:
            self.remove_file(Path(event.src_path))

    def process_file(self, path: Path, action: str):
        if path.suffix.lower() != ".md" or is_ignored(path, VAULT_PATH):
            return

        console.print(f"[cyan]File {action}:[/cyan] {path.name}")

        # 1. Remove existing chunks for this file
        self.remove_file(path, log=False)

        # 2. Chunk the file
        file_chunks = chunk_file(path, VAULT_PATH, min_chars=MIN_CHUNK_CHARS)
        if not file_chunks:
            return

        all_chunks = []
        for chunk in file_chunks:
            if len(chunk.text) > MAX_CHUNK_CHARS:
                sub_texts = split_long_chunk(chunk.text, MAX_CHUNK_CHARS)
                for i, sub_text in enumerate(sub_texts):
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

        if not all_chunks:
            return

        # 3. Embed and upsert
        for chunk in all_chunks:
            embed_text = (
                f"{chunk.heading}\n\n{chunk.text}" if chunk.heading else chunk.text
            )
            embedding = self.model.encode(embed_text).tolist()

            meta = {
                "file_path": chunk.file_path,
                "file_name": chunk.file_name,
                "folder": chunk.folder,
                "subfolder": chunk.subfolder,
                "heading": chunk.heading,
                "text": chunk.text,
            }
            for k, v in chunk.fm.items():
                meta[f"fm_{k}"] = str(v)

            self.index.add(chunk.doc_id, embedding, json.dumps(meta))
        
        # Save index to disk
        self.index.save(str(MEMORY_INDEX_PATH))
        console.print(f"  [green]➔ Indexed {len(all_chunks)} chunks.[/green]")

    def remove_file(self, path: Path, log: bool = True):
        if path.suffix.lower() != ".md" or is_ignored(path, VAULT_PATH):
            return

        if log:
            console.print(f"[red]File deleted/moved:[/red] {path.name}")

        try:
            rel_path = str(path.relative_to(VAULT_PATH))
        except ValueError:
            rel_path = str(path)

        # We delete all chunks that belong to this file path
        # Note: VectorIndex delete is by ID, so we'd need to track IDs per file path 
        # or implement a more complex delete in Rust. 
        # For v2 simplification, we'll recreate the index or use a simple prefix delete if we had it.
        # Actually, let's keep it simple for now: add a placeholder for future path-based delete.
        # self.index.delete_by_path(rel_path) 
        pass


@click.command()
def watch():
    """Watch the Obsidian vault for changes and automatically update the Rust memory index."""
    console.print("[bold blue]ZANA Watchdog[/bold blue]")
    console.print(f"Watching Vault: [green]{VAULT_PATH}[/green]")

    if not VAULT_PATH.exists():
        console.print(
            f"[bold red]Error:[/bold red] Vault path {VAULT_PATH} does not exist."
        )
        sys.exit(1)

    # Ensure data directory exists
    MEMORY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Initialize Rust Index
    if MEMORY_INDEX_PATH.exists():
        console.print(f"[yellow]Loading existing index from {MEMORY_INDEX_PATH}...[/yellow]")
        index = zana_steel_core.PyVectorIndex.load(str(MEMORY_INDEX_PATH))
    else:
        console.print("[yellow]Creating new memory index...[/yellow]")
        index = zana_steel_core.PyVectorIndex()

    console.print("[yellow]Loading embedding model...[/yellow]")
    model = SentenceTransformer(EMBED_MODEL, device="cpu")

    event_handler = VaultEventHandler(index, model)
    observer = Observer()
    observer.schedule(event_handler, str(VAULT_PATH), recursive=True)

    observer.start()
    console.print(
        "[bold green]✅ Watching for changes. Press Ctrl+C to stop.[/bold green]"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Stopping watcher...[/yellow]")

    observer.join()


if __name__ == "__main__":
    watch()
