"""
memory_lite.py — SQLite FTS5 memory backend for SPROUT tier.

Provides semantic-like text search without Docker, ChromaDB or any external service.
All data lives in ~/.zana/memory_lite.db — portable, sovereign, offline.
"""

import json
import sqlite3
from pathlib import Path

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    collection  TEXT    NOT NULL DEFAULT 'zana_vault',
    source      TEXT    DEFAULT '',
    content     TEXT    NOT NULL,
    metadata    TEXT    DEFAULT '{}',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content,
    source,
    collection UNINDEXED,
    content='documents',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, content, source, collection)
    VALUES (new.id, new.content, new.source, new.collection);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, content, source, collection)
    VALUES ('delete', old.id, old.content, old.source, old.collection);
END;
"""


class MemoryLiteDB:
    """SQLite FTS5-backed memory store for ZANA SPROUT tier.

    All data is stored in ~/.zana/memory_lite.db.
    No external services required — fully offline and sovereign.
    """

    DB_PATH = Path.home() / ".zana" / "memory_lite.db"

    def __init__(self) -> None:
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.DB_PATH))
        self._conn.row_factory = sqlite3.Row
        # Enable WAL for better concurrent read performance
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._bootstrap()

    def _bootstrap(self) -> None:
        """Create tables and triggers if they do not exist."""
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        source: str = "",
        collection: str = "zana_vault",
        metadata: dict | None = None,
    ) -> int:
        """Insert a document into the store.

        Triggers automatically keep FTS5 index in sync.

        Returns:
            The rowid of the newly inserted document.
        """
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        cur = self._conn.execute(
            "INSERT INTO documents (collection, source, content, metadata) VALUES (?, ?, ?, ?)",
            (collection, source, content, meta_json),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def add_episodic(self, role: str, content: str) -> int:
        """Shortcut: add a message to the 'episodic' collection.

        Args:
            role:    Speaker role (e.g. "user", "assistant").
            content: Message text.

        Returns:
            The rowid of the inserted record.
        """
        return self.add(content=content, source=role, collection="episodic")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        collection: str = "zana_vault",
        n: int = 5,
    ) -> list[dict]:
        """Full-text search using FTS5 BM25 ranking.

        Args:
            query:      Search string (FTS5 MATCH syntax supported).
            collection: Restrict results to this collection name.
            n:          Maximum number of results to return.

        Returns:
            List of dicts with keys: id, source, content, metadata, score.
            ``score`` is normalised to [0, 1] where 1 is most relevant.
            The list is ordered from most to least relevant.
        """
        if not query or not query.strip():
            return []

        # Escape FTS5 special characters so plain strings work safely.
        # Wrap each token in double quotes to avoid operator confusion.
        safe_query = " ".join(f'"{tok}"' for tok in query.split())

        sql = """
            SELECT
                d.id,
                d.source,
                d.content,
                d.metadata,
                d.created_at,
                fts.rank AS rank
            FROM documents_fts fts
            JOIN documents d ON d.id = fts.rowid
            WHERE documents_fts MATCH ?
              AND fts.collection = ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            rows = self._conn.execute(sql, (safe_query, collection, n)).fetchall()
        except sqlite3.OperationalError:
            # Malformed FTS query — return empty rather than crashing
            return []

        if not rows:
            return []

        # FTS5 rank is negative; more negative = more relevant.
        # Normalise to [0, 1]: best result → 1.0, worst → closer to 0.
        ranks = [r["rank"] for r in rows]
        min_rank = min(ranks)
        max_rank = max(ranks)
        rank_range = max_rank - min_rank  # will be 0 if single result

        results: list[dict] = []
        for row in rows:
            if rank_range == 0:
                score = 1.0
            else:
                # Map [min_rank, max_rank] → [1.0, 0.0]
                score = 1.0 - (row["rank"] - min_rank) / rank_range

            try:
                meta = json.loads(row["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}

            results.append(
                {
                    "id": row["id"],
                    "source": row["source"] or "—",
                    "content": row["content"],
                    "metadata": meta,
                    "created_at": row["created_at"],
                    "score": round(score, 4),
                }
            )

        return results

    def recall(self, n: int = 10) -> list[dict]:
        """Return the last *n* records from the 'episodic' collection.

        Args:
            n: Maximum number of records to return (most recent first).

        Returns:
            List of dicts with keys: id, source, content, created_at.
        """
        sql = """
            SELECT id, source, content, created_at
            FROM documents
            WHERE collection = 'episodic'
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self._conn.execute(sql, (n,)).fetchall()
        return [
            {
                "id": row["id"],
                "source": row["source"] or "—",
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def stats(self) -> dict:
        """Return aggregate statistics for the database.

        Returns:
            Dict with keys:
            - ``collections``: mapping of collection name → document count.
            - ``total``: total document count across all collections.
            - ``db_path``: absolute path to the SQLite file (str).
            - ``db_size_mb``: file size in megabytes (float).
        """
        rows = self._conn.execute(
            "SELECT collection, COUNT(*) AS cnt FROM documents GROUP BY collection"
        ).fetchall()

        collections: dict[str, int] = {row["collection"]: row["cnt"] for row in rows}
        total: int = sum(collections.values())

        db_path = str(self.DB_PATH)
        try:
            db_size_mb = round(self.DB_PATH.stat().st_size / (1024 * 1024), 3)
        except FileNotFoundError:
            db_size_mb = 0.0

        return {
            "collections": collections,
            "total": total,
            "db_path": db_path,
            "db_size_mb": db_size_mb,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()


def get_db() -> MemoryLiteDB:
    """Get a MemoryLiteDB instance. Creates the DB file if it does not exist."""
    return MemoryLiteDB()
