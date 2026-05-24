from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

_DB_PATH = Path.home() / ".zana" / "memory_lite.db"


class MemoryLiteDB:
    DB_PATH: Path = _DB_PATH  # class-level for monkeypatching in tests

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or self.__class__.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
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
        """)
        self._conn.commit()

    # ── Write ────────────────────────────────────────────────────────────────

    def add(
        self,
        content: str,
        source: str = "cli",
        collection: str = "zana_vault",
        metadata: dict | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO documents (content, source, collection, metadata) VALUES (?, ?, ?, ?)",
            (content, source, collection, json.dumps(metadata or {})),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def add_episodic(self, role: str, content: str) -> int:
        return self.add(content, source=role, collection="episodic")

    def update_doc(
        self,
        doc_id: int,
        content: str | None = None,
        source: str | None = None,
    ) -> bool:
        sets, vals = [], []
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
    ) -> list[dict]:
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

    def recall(self, n: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT content, source, created_at FROM documents"
            " WHERE collection = 'episodic' ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [{"content": r[0], "role": r[1], "timestamp": r[2]} for r in rows]

    def get_session_history(self, session_id: str, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT user_query, aeon_response, timestamp FROM session_history"
            " WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def export_docs(self, collection: str | None = None) -> list[dict]:
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

    def import_docs(self, docs: list[dict]) -> int:
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

    def stats(self) -> dict:
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
    return MemoryLiteDB()


def is_sqlite_vec_available() -> bool:
    """Return True if sqlite-vec extension is available for vector search."""
    try:
        import sqlite_vec  # noqa: F401

        return True
    except ImportError:
        return False
