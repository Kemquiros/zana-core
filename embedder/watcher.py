import sys
import time
from pathlib import Path

import chromadb
import click
from rich.console import Console
from sentence_transformers import SentenceTransformer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_file
from config import (
    CHROMA_HOST,
    CHROMA_PORT,
    COLLECTION_NAME,
    EMBED_MODEL,
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    VAULT_PATH,
)
from main import is_ignored, split_long_chunk

console = Console()

class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, chroma_client, collection, model):
        super().__init__()
        self.chroma_client = chroma_client
        self.collection = collection
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
                        fm=chunk.fm
                    )
                    all_chunks.append(sub_chunk)
            else:
                all_chunks.append(chunk)

        if not all_chunks:
            return

        # 3. Embed and upsert
        ids = []
        documents = []
        metadatas = []
        
        for chunk in all_chunks:
            ids.append(chunk.doc_id)
            embed_text = f"{chunk.heading}\n\n{chunk.text}" if chunk.heading else chunk.text
            documents.append(embed_text)
            
            meta = {
                "file_path": chunk.file_path,
                "file_name": chunk.file_name,
                "folder": chunk.folder,
                "subfolder": chunk.subfolder,
                "heading": chunk.heading,
            }
            for k, v in chunk.fm.items():
                meta[f"fm_{k}"] = str(v)
            metadatas.append(meta)
            
        embeddings = self.model.encode(documents).tolist()
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        console.print(f"  [green]➔ Upserted {len(all_chunks)} chunks.[/green]")

    def remove_file(self, path: Path, log: bool = True):
        if path.suffix.lower() != ".md" or is_ignored(path, VAULT_PATH):
            return
            
        if log:
            console.print(f"[red]File deleted/moved:[/red] {path.name}")
            
        try:
            rel_path = str(path.relative_to(VAULT_PATH))
        except ValueError:
            rel_path = str(path)
            
        # We delete all chunks that match the file_path metadata
        try:
            self.collection.delete(
                where={"file_path": rel_path}
            )
            if log:
                console.print(f"  [green]➔ Removed chunks for {rel_path}.[/green]")
        except Exception as e:
            if log:
                console.print(f"  [yellow]➔ Error removing chunks: {e}[/yellow]")


@click.command()
def watch():
    """Watch the Obsidian vault for changes and automatically update ChromaDB."""
    console.print(f"[bold blue]ZANA Watchdog[/bold blue]")
    console.print(f"Watching Vault: [green]{VAULT_PATH}[/green]")
    
    if not VAULT_PATH.exists():
        console.print(f"[bold red]Error:[/bold red] Vault path {VAULT_PATH} does not exist.")
        sys.exit(1)

    # Initialize ChromaDB client
    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        chroma_client.heartbeat()
    except Exception as e:
        console.print(f"[bold red]Error connecting to ChromaDB:[/bold red] {e}")
        sys.exit(1)

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    console.print("[yellow]Loading embedding model...[/yellow]")
    model = SentenceTransformer(EMBED_MODEL, device="cpu")
    
    event_handler = VaultEventHandler(chroma_client, collection, model)
    observer = Observer()
    observer.schedule(event_handler, str(VAULT_PATH), recursive=True)
    
    observer.start()
    console.print("[bold green]✅ Watching for changes. Press Ctrl+C to stop.[/bold green]")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Stopping watcher...[/yellow]")
        
    observer.join()

if __name__ == "__main__":
    watch()
