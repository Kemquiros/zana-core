"""Split markdown files into semantic chunks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter


@dataclass
class Chunk:
    doc_id: str          # unique ID: "relative/path.md::chunk_N"
    text: str            # chunk text (heading included)
    heading: str         # the ## heading this chunk belongs to (or "" for intro)
    file_path: str       # relative path from vault root
    file_name: str       # just the stem
    folder: str          # top-level folder name
    subfolder: str       # second-level folder name (or "")
    fm: dict = field(default_factory=dict)  # frontmatter metadata


def _relative(path: Path, vault_root: Path) -> str:
    try:
        return str(path.relative_to(vault_root))
    except ValueError:
        return str(path)


def _folder_parts(rel_path: str) -> tuple[str, str]:
    parts = Path(rel_path).parts
    folder = parts[0] if len(parts) > 1 else ""
    subfolder = parts[1] if len(parts) > 2 else ""
    return folder, subfolder


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Return list of (heading, content) pairs. First section has heading=""."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{1,3} ", line):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line.strip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return sections


def chunk_file(path: Path, vault_root: Path, min_chars: int = 80) -> list[Chunk]:
    """Parse a markdown file and return its chunks."""
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return []

    content = post.content.strip()
    if not content:
        return []

    rel_path = _relative(path, vault_root)
    folder, subfolder = _folder_parts(rel_path)

    # Frontmatter metadata (keep only string/list values for ChromaDB)
    fm_clean: dict = {}
    for k, v in post.metadata.items():
        if isinstance(v, (str, int, float)):
            fm_clean[k] = str(v)
        elif isinstance(v, list):
            fm_clean[k] = ", ".join(str(x) for x in v)

    sections = _split_by_headings(content)
    chunks: list[Chunk] = []

    for idx, (heading, body) in enumerate(sections):
        if len(body) < min_chars:
            continue

        chunk_id = f"{rel_path}::{idx}"
        chunks.append(
            Chunk(
                doc_id=chunk_id,
                text=body,
                heading=heading,
                file_path=rel_path,
                file_name=path.stem,
                folder=folder,
                subfolder=subfolder,
                fm=fm_clean,
            )
        )

    # If the file produced no chunks (short file), embed it whole
    if not chunks and len(content) >= min_chars:
        chunks.append(
            Chunk(
                doc_id=f"{rel_path}::0",
                text=content,
                heading="",
                file_path=rel_path,
                file_name=path.stem,
                folder=folder,
                subfolder=subfolder,
                fm=fm_clean,
            )
        )

    return chunks
