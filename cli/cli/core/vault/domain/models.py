"""Vault domain models — pure data, no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SourceKind(str, Enum):
    FOLDER    = "folder"
    OBSIDIAN  = "obsidian"
    LOGSEQ    = "logseq"
    GIT_REPO  = "git_repo"
    CHATGPT   = "chatgpt"
    CLAUDE    = "claude"
    NOTION    = "notion"
    ROAM      = "roam"
    EMPTY     = "empty"


@dataclass
class VaultSource:
    path: Path
    kind: SourceKind
    label: str
    file_count: int = 0
    size_mb: float = 0.0
    selected: bool = False

    @property
    def display(self) -> str:
        size_str = f"{self.size_mb:.1f} MB" if self.size_mb >= 1 else f"{int(self.size_mb * 1024)} KB"
        return f"{self.label} ({self.file_count:,} archivos · {size_str})"


@dataclass
class VaultDocument:
    path: Path
    content: str
    title: str = ""
    modified_at: float = 0.0
    word_count: int = 0

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self.path.stem
        if not self.word_count:
            self.word_count = len(self.content.split())


@dataclass
class VaultIndex:
    source_paths: list[Path] = field(default_factory=list)
    total_docs: int = 0
    total_words: int = 0
    db_path: Path = field(default_factory=lambda: Path.home() / ".zana" / "vault.db")
    ready: bool = False