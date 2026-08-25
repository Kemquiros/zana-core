"""memory_lite.py — SQLite FTS5 + optional sqlite-vec memory backend.

SPROUT: keyword search via FTS5 (always available, no dependencies).
GROVE:  semantic search via sqlite-vec + Ollama embeddings (optional, no
Docker). Install the semantic layer with: ``pip install vecanova-zana[grove]``
or run ``zana upgrade --grove``.

History note (Issue #84): commit d3b58da (Zenith v3.14.0) removed the vector
layer from this module while tests/test_grove_semantic.py and the live CLI
(``zana memory reindex``, ``zana upgrade --grove``) still consumed it. This
restoration brings back the GROVE API on top of the current schema, keeping
the newer additions of this file (session_history, stats with oldest/newest,
update_doc, add_session_record) intact.
"""

from __future__ import annotations

import json
import os
import sqlite3
import struct
from pathlib import Path
from typing import Any

_DB_PATH = Path.home() / ".zana" / "memory_lite.db"

_EMBED_MODEL = "nomic-embed-text"
_EMBED_DIM = 768  # nomic-embed-text output dimension
_OLLAMA_URL = "http://localhost:11434/api/embeddings"

_VEC_TABLE_SQL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec USING vec0(embedding float[{dim}]);"
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content    TEXT NOT NULL,
    source     TEXT DEFAULT 'cli',
    collection TEXT DEFAULT 'zana_vault',
    metadata   TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS session_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    user_query   TEXT NOT NULL,
    aeon_response TEXT NOT NULL,
    timestamp    TEXT
);
CREATE TRIGGER IF NOT EXISTS set_timestamp
    AFTER INSERT ON session_history
BEGIN
    UPDATE session_history SET timestamp = datetime('now') WHERE id = new.id;
END;
CREATE TABLE IF NOT EXISTS _vec_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# GROVE helpers (sqlite-vec + Ollama)
# ---------------------------------------------------------------------------


def _load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension into an open connection. True on success."""
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
    """Return True if the Ollama embedding endpoint responds."""
    return _get_ollama_embedding("test") is not None


# ---------------------------------------------------------------------------
# Memory store
# ---------------------------------------------------------------------------


class MemoryLiteDB:
    """SQLite FTS5 + optional sqlite-vec memory store.

    SPROUT: keyword search (always available).
    GROVE:  semantic search via sqlite-vec + Ollama (when both are installed).

    All data lives in ~/.zana/memory_lite.db — portable, sovereign, offline.
    """

    DB_PATH: Path = _DB_PATH  # class-level for monkeypatching in tests

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or self.__class__.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._vec_loaded = _load_sqlite_vec(self._conn)
        self._init_db()

    def _init_db(self) -> None:
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

    # ── Vector index helpers ──────────────────────────────────────────────────

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
        """Store an embedding for an existing document. True on success."""
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
        """Regenerate embeddings for all vault docs via Ollama. Returns count."""
        if not self.has_vector_index():
            return 0
        rows = self._conn.execute(
            "SELECT id, content FROM documents WHERE collection='zana_vault'"
        ).fetchall()
        indexed = 0
        for row in rows:
            emb = _get_ollama_embedding(row["content"])
            if emb and self.index_memory(int(row["id"]), emb):
                indexed += 1
        return indexed

    # ── Write ────────────────────────────────────────────────────────────────

    def add(
        self,
        content: str,
        source: str = "cli",
        collection: str = "zana_vault",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert a document. If sqlite-vec + Ollama are available and the
        collection is 'zana_vault', also indexes the embedding. Returns rowid."""
        cur = self._conn.execute(
            "INSERT INTO documents (content, source, collection, metadata) VALUES (?, ?, ?, ?)",
            (content, source, collection, json.dumps(metadata or {})),
        )
        self._conn.commit()
        doc_id: int = cur.lastrowid  # type: ignore[assignment]

        if self.has_vector_index() and collection == "zana_vault":
            emb = _get_ollama_embedding(content)
            if emb:
                self.index_memory(doc_id, emb)

        return doc_id

    def add_episodic(self, role: str, content: str) -> int:
        return self.add(content, source=role, collection="episodic")

    def update_doc(
        self,
        doc_id: int,
        content: str | None = None,
        source: str | None = None,
    ) -> bool:
        sets: list[str] = []
        vals: list[Any] = []
        if content is not None:
            sets.append("content = ?")
            vals.append(content)
        if source is not None:
            sets.append("source = ?")
            vals.append(source)
        if not sets:
            return False
        vals.append(doc_id)
        cur = self._conn.execute(
            f"UPDATE documents SET {', '.join(sets)} WHERE id = ?", vals
        )
        self._conn.commit()
        return cur.rowcount > 0

    def add_session_record(self, session_id: str, user: str, aeon: str) -> None:
        self._conn.execute(
            "INSERT INTO session_history (session_id, user_query, aeon_response) VALUES (?, ?, ?)",
            (session_id, user, aeon),
        )
        self._conn.commit()

    # ── Delete ───────────────────────────────────────────────────────────────

    def delete(self, doc_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear(self, collection: str | None = None) -> int:
        if collection:
            cur = self._conn.execute(
                "DELETE FROM documents WHERE collection = ?", (collection,)
            )
        else:
            cur = self._conn.execute("DELETE FROM documents")
        self._conn.commit()
        return cur.rowcount

    # ── Read ─────────────────────────────────────────────────────────────────

    def search(
        self, query: str, collection: str = "zana_vault", n: int = 5
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT content, source, collection, id FROM documents"
            " WHERE content LIKE ? AND collection = ? LIMIT ?",
            (f"%{query}%", collection, n),
        ).fetchall()
        return [
            {
                "content": r[0],
                "source": r[1],
                "collection": r[2],
                "id": r[3],
                "score": 1.0,
            }
            for r in rows
        ]

    def search_semantic(
        self,
        query: str,
        collection: str = "zana_vault",
        n: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search via sqlite-vec cosine similarity + Ollama embeddings.

        Falls back to keyword search when sqlite-vec is unavailable, Ollama is
        unreachable, or the vector query fails. Always returns a list — never
        crashes.
        """
        if not self.has_vector_index():
            return self.search(query, collection=collection, n=n)

        emb = _get_ollama_embedding(query)
        if emb is None:
            return self.search(query, collection=collection, n=n)

        blob = _serialize_vec(emb)
        try:
            vec_rows = self._conn.execute(
                "SELECT rowid, distance FROM memory_vec"
                " WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
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
            "SELECT id, source, content, metadata, created_at FROM documents"
            f" WHERE id IN ({placeholders}) AND collection = ?",
            (*ids, collection),
        ).fetchall()

        results: list[dict[str, Any]] = []
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

    def recall(self, n: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT content, source, created_at FROM documents"
            " WHERE collection = 'episodic' ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [{"content": r[0], "role": r[1], "timestamp": r[2]} for r in rows]

    def get_session_history(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT user_query, aeon_response, timestamp FROM session_history"
            " WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def export_docs(self, collection: str | None = None) -> list[dict[str, Any]]:
        if collection:
            rows = self._conn.execute(
                "SELECT id, content, source, collection, metadata, created_at"
                " FROM documents WHERE collection = ? ORDER BY id",
                (collection,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, content, source, collection, metadata, created_at"
                " FROM documents ORDER BY id"
            ).fetchall()
        return [
            {
                "id": r[0],
                "content": r[1],
                "source": r[2],
                "collection": r[3],
                "metadata": json.loads(r[4] or "{}"),
                "created_at": r[5],
            }
            for r in rows
        ]

    def import_docs(self, docs: list[dict[str, Any]]) -> int:
        count = 0
        for doc in docs:
            content = doc.get("content", "").strip()
            if not content:
                continue
            self._conn.execute(
                "INSERT INTO documents (content, source, collection, metadata) VALUES (?, ?, ?, ?)",
                (
                    content,
                    doc.get("source", "import"),
                    doc.get("collection", "zana_vault"),
                    json.dumps(doc.get("metadata", {})),
                ),
            )
            count += 1
        self._conn.commit()
        return count

    def stats(self) -> dict[str, Any]:
        total_row = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        total = total_row[0] if total_row else 0

        coll_rows = self._conn.execute(
            "SELECT collection, COUNT(*) FROM documents GROUP BY collection"
        ).fetchall()
        collections = {r[0]: r[1] for r in coll_rows}

        date_row = self._conn.execute(
            "SELECT MIN(created_at), MAX(created_at),"
            "       (SELECT id FROM documents ORDER BY id ASC LIMIT 1),"
            "       (SELECT id FROM documents ORDER BY id DESC LIMIT 1)"
            " FROM documents"
        ).fetchone()

        oldest = date_row[0] if date_row and date_row[0] else None
        newest = date_row[1] if date_row and date_row[1] else None
        oldest_id = date_row[2] if date_row else None
        newest_id = date_row[3] if date_row else None

        db_path_str = str(self.db_path)
        try:
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        except OSError:
            db_size_mb = 0.0

        return {
            "total": total,
            "collections": collections,
            "oldest": oldest,
            "newest": newest,
            "oldest_id": oldest_id,
            "newest_id": newest_id,
            "db_path": db_path_str,
            "db_size_mb": db_size_mb,
        }

    def close(self) -> None:
        self._conn.close()


def get_db() -> MemoryLiteDB:
    """Get a MemoryLiteDB instance. Creates the DB file if it does not exist."""
    return MemoryLiteDB()
