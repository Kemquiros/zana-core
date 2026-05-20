"""
memory_lite.py — SQLite FTS5 + optional sqlite-vec memory backend for SPROUT/GROVE tier.

SPROUT: keyword search via FTS5 (always available, no dependencies).
GROVE:  semantic search via sqlite-vec + Ollama embeddings (optional, no Docker).

Install semantic layer: pip install vecanova-zana[grove]
"""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_EMBED_MODEL = "nomic-embed-text"
_EMBED_DIM = 768  # nomic-embed-text output dimension
_OLLAMA_URL = "http://localhost:11434/api/embeddings"

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

CREATE TABLE IF NOT EXISTS _vec_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_VEC_TABLE_SQL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec USING vec0(embedding float[{dim}]);"
)


def _load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension into an open connection. Returns True on success."""
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


def _get_ollama_embedding(text: str) -> list[float] | None:
    """Request embedding from local Ollama. Returns None if unavailable."""
    try:
        import httpx

        r = httpx.post(
            _OLLAMA_URL,
            json={"model": _EMBED_MODEL, "prompt": text},
            timeout=10.0,
        )
        if r.status_code == 200:
            emb = r.json().get("embedding")
            if isinstance(emb, list) and len(emb) > 0:
                return emb
    except Exception:
        pass
    return None


def _serialize_vec(embedding: list[float]) -> bytes:
    """Serialize a float list to little-endian bytes for sqlite-vec."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def is_sqlite_vec_available() -> bool:
    """Return True if sqlite-vec can be loaded in a fresh connection."""
    try:
        conn = sqlite3.connect(":memory:")
        result = _load_sqlite_vec(conn)
        conn.close()
        return result
    except Exception:
        return False


def is_ollama_available() -> bool:
    """Return True if Ollama embedding endpoint responds."""
    return _get_ollama_embedding("test") is not None


class MemoryLiteDB:
    """SQLite FTS5 + optional sqlite-vec memory store.

    SPROUT: keyword search (always available).
    GROVE:  semantic search via sqlite-vec + Ollama (when both are installed).

    All data lives in ~/.zana/memory_lite.db — portable, sovereign, offline.
    """

    DB_PATH = Path.home() / ".zana" / "memory_lite.db"

    def __init__(self, db_path: Path | None = None) -> None:
        path = db_path or self.DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._vec_loaded = _load_sqlite_vec(self._conn)
        self._bootstrap()

    def _bootstrap(self) -> None:
        """Create tables and triggers if they do not exist."""
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        if self._vec_loaded:
            self._init_vec_table()

    def _init_vec_table(self) -> None:
        """Create the vector table at the stored dimension (default: 768)."""
        row = self._conn.execute(
            "SELECT value FROM _vec_meta WHERE key='dim'"
        ).fetchone()
        dim = int(row["value"]) if row else _EMBED_DIM
        if not row:
            self._conn.execute(
                "INSERT OR IGNORE INTO _vec_meta(key,value) VALUES('dim',?)",
                (str(dim),),
            )
            self._conn.commit()
        try:
            self._conn.execute(_VEC_TABLE_SQL.format(dim=dim))
            self._conn.commit()
        except Exception:
            self._vec_loaded = False

    # ------------------------------------------------------------------
    # Vector index helpers
    # ------------------------------------------------------------------

    def has_vector_index(self) -> bool:
        """Return True if sqlite-vec is loaded and the vector table exists."""
        if not self._vec_loaded:
            return False
        try:
            self._conn.execute("SELECT count(*) FROM memory_vec").fetchone()
            return True
        except Exception:
            return False

    def index_memory(self, doc_id: int, embedding: list[float]) -> bool:
        """Store an embedding for an existing document. Returns True on success."""
        if not self.has_vector_index():
            return False
        try:
            blob = _serialize_vec(embedding)
            self._conn.execute(
                "INSERT OR REPLACE INTO memory_vec(rowid, embedding) VALUES(?, ?)",
                (doc_id, blob),
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def rebuild_vector_index(self) -> int:
        """Regenerate embeddings for all documents via Ollama. Returns count indexed."""
        if not self.has_vector_index():
            return 0
        rows = self._conn.execute(
            "SELECT id, content FROM documents WHERE collection='zana_vault'"
        ).fetchall()
        indexed = 0
        for row in rows:
            emb = _get_ollama_embedding(row["content"])
            if emb and self.index_memory(row["id"], emb):
                indexed += 1
        return indexed

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
        """Insert a document. FTS5 trigger keeps keyword index in sync.
        If sqlite-vec + Ollama are available, also indexes the embedding.

        Returns the rowid of the inserted document.
        """
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        cur = self._conn.execute(
            "INSERT INTO documents (collection, source, content, metadata) VALUES (?, ?, ?, ?)",
            (collection, source, content, meta_json),
        )
        self._conn.commit()
        doc_id: int = cur.lastrowid  # type: ignore[assignment]

        if self.has_vector_index() and collection == "zana_vault":
            emb = _get_ollama_embedding(content)
            if emb:
                self.index_memory(doc_id, emb)

        return doc_id

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

    def search_semantic(
        self,
        query: str,
        collection: str = "zana_vault",
        n: int = 5,
    ) -> list[dict]:
        """Semantic search using sqlite-vec cosine similarity + Ollama embeddings.

        Falls back to FTS5 keyword search if sqlite-vec is not loaded or
        Ollama is not reachable. Always returns results — never crashes.

        Args:
            query:      Natural-language search query.
            collection: Restrict to this collection.
            n:          Maximum results.

        Returns:
            List of dicts with keys: id, source, content, metadata, created_at, score.
            ``score`` is distance (lower = more similar) when semantic, or BM25 when fallback.
        """
        if not self.has_vector_index():
            return self.search(query, collection=collection, n=n)

        emb = _get_ollama_embedding(query)
        if emb is None:
            return self.search(query, collection=collection, n=n)

        blob = _serialize_vec(emb)
        try:
            vec_rows = self._conn.execute(
                "SELECT rowid, distance FROM memory_vec WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                (blob, n * 2),
            ).fetchall()
        except Exception:
            return self.search(query, collection=collection, n=n)

        if not vec_rows:
            return self.search(query, collection=collection, n=n)

        ids = [r["rowid"] for r in vec_rows]
        dist_by_id = {r["rowid"]: r["distance"] for r in vec_rows}

        placeholders = ",".join("?" * len(ids))
        doc_rows = self._conn.execute(
            f"SELECT id, source, content, metadata, created_at FROM documents"
            f" WHERE id IN ({placeholders}) AND collection = ?",
            (*ids, collection),
        ).fetchall()

        results = []
        for row in doc_rows:
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
                    "score": round(dist_by_id.get(row["id"], 0.0), 4),
                    "mode": "semantic",
                }
            )

        results.sort(key=lambda x: x["score"])
        return results[:n]

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

    def delete(self, doc_id: int) -> bool:
        """Delete a document by ID.

        Returns True if a row was deleted, False if the ID did not exist.
        """
        cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear(self, collection: str | None = None) -> int:
        """Delete all documents in *collection*, or every document if collection is None.

        Returns the number of rows deleted.
        """
        if collection is None:
            cur = self._conn.execute("DELETE FROM documents")
        else:
            cur = self._conn.execute(
                "DELETE FROM documents WHERE collection = ?", (collection,)
            )
        self._conn.commit()
        # Keep FTS5 index in sync after bulk delete
        self._conn.execute(
            "INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')"
        )
        self._conn.commit()
        return cur.rowcount

    def export_docs(self, collection: str | None = None) -> list[dict]:
        """Return all documents (optionally filtered by collection) as plain dicts."""
        if collection is None:
            rows = self._conn.execute(
                "SELECT id, collection, source, content, metadata, created_at FROM documents"
                " ORDER BY created_at"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, collection, source, content, metadata, created_at FROM documents"
                " WHERE collection = ? ORDER BY created_at",
                (collection,),
            ).fetchall()

        result = []
        for row in rows:
            try:
                meta = json.loads(row["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            result.append(
                {
                    "id": row["id"],
                    "collection": row["collection"],
                    "source": row["source"],
                    "content": row["content"],
                    "metadata": meta,
                    "created_at": row["created_at"],
                }
            )
        return result

    def import_docs(self, docs: list[dict]) -> int:
        """Bulk-insert documents from a list of dicts.

        Accepted keys: collection, source, content, metadata (optional).
        Returns the number of documents inserted.
        """
        inserted = 0
        for doc in docs:
            content = doc.get("content", "")
            if not content:
                continue
            self.add(
                content=content,
                source=doc.get("source", ""),
                collection=doc.get("collection", "zana_vault"),
                metadata=doc.get("metadata") or {},
            )
            inserted += 1
        return inserted

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
