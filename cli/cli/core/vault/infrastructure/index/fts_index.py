"""
SQLite FTS5 vault index — zero external dependencies.
Level 0: always available. Level 1+ uses ChromaDB.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Iterator

from cli.core.vault.domain.models import VaultDocument, VaultIndex

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts USING fts5(
    path UNINDEXED,
    title,
    content,
    tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS vault_meta (
    path TEXT PRIMARY KEY,
    modified_at REAL,
    word_count INTEGER
);
"""


class FTSIndex:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def index_documents(
        self,
        docs: list[VaultDocument],
        progress_cb: "Callable[[int, int], None] | None" = None,
    ) -> int:
        total = len(docs)
        indexed = 0
        cursor = self._conn.cursor()

        for i, doc in enumerate(docs):
            # Skip if unchanged
            cursor.execute(
                "SELECT modified_at FROM vault_meta WHERE path = ?",
                (str(doc.path),),
            )
            row = cursor.fetchone()
            if row and row[0] == doc.modified_at:
                if progress_cb:
                    progress_cb(i + 1, total)
                continue

            # Upsert into FTS
            cursor.execute(
                "DELETE FROM vault_fts WHERE path = ?", (str(doc.path),)
            )
            cursor.execute(
                "INSERT INTO vault_fts (path, title, content) VALUES (?, ?, ?)",
                (str(doc.path), doc.title, doc.content[:50_000]),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO vault_meta (path, modified_at, word_count) VALUES (?, ?, ?)",
                (str(doc.path), doc.modified_at, doc.word_count),
            )
            indexed += 1
            if progress_cb:
                progress_cb(i + 1, total)

        self._conn.commit()
        return indexed

    def search(self, query: str, limit: int = 10) -> list[dict]:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                SELECT path, title,
                       snippet(vault_fts, 2, '[', ']', '...', 32) as excerpt,
                       rank
                FROM vault_fts
                WHERE vault_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            )
            rows = cursor.fetchall()
            return [
                {"path": r[0], "title": r[1], "excerpt": r[2], "score": r[3]}
                for r in rows
            ]
        except sqlite3.OperationalError:
            return []

    def total_docs(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vault_meta")
        return cur.fetchone()[0]

    def total_words(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT SUM(word_count) FROM vault_meta")
        result = cur.fetchone()[0]
        return result or 0

    def find_memory_echo(self) -> dict | None:
        """Find a note that resonates with the user's original motivation.
        Returns a random note that mentions building, memory, or sovereignty."""
        keywords = ["construir", "build", "quiero", "sistema", "memoria",
                    "propio", "independiente", "soberanía", "autonomía",
                    "recordar", "aprender", "crecer"]
        cur = self._conn.cursor()
        for kw in keywords:
            try:
                cur.execute(
                    """
                    SELECT path, title,
                           snippet(vault_fts, 2, '', '', '', 20) as excerpt,
                           modified_at
                    FROM vault_fts
                    WHERE vault_fts MATCH ?
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    (kw,),
                )
                row = cur.fetchone()
                if row and row[2].strip():
                    return {
                        "path": row[0],
                        "title": row[1],
                        "excerpt": row[2],
                        "modified_at": row[3],
                    }
            except sqlite3.OperationalError:
                continue
        return None