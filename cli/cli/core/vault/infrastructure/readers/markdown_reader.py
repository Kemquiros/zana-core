"""Read .md and .txt files into VaultDocuments."""
from __future__ import annotations

import os
from pathlib import Path

from cli.core.vault.domain.models import VaultDocument


def read_markdown(path: Path) -> VaultDocument | None:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return None
        stat = path.stat()
        return VaultDocument(
            path=path,
            content=content,
            title=path.stem,
            modified_at=stat.st_mtime,
        )
    except Exception:
        return None


SUPPORTED_EXTENSIONS = {".md", ".txt", ".markdown"}


def iter_documents(root: Path) -> list[VaultDocument]:
    docs: list[VaultDocument] = []
    try:
        for dirpath, _dirs, files in os.walk(root):
            # Skip hidden dirs like .git, .obsidian data
            _dirs[:] = [d for d in _dirs if not d.startswith(".")]
            for fname in files:
                fpath = Path(dirpath) / fname
                if fpath.suffix.lower() in SUPPORTED_EXTENSIONS:
                    doc = read_markdown(fpath)
                    if doc:
                        docs.append(doc)
    except PermissionError:
        pass
    return docs