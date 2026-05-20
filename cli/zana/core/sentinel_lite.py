"""
sentinel_lite.py — SQLite ring buffer for Sentinel events (SPROUT tier).

Stores the last MAX_EVENTS events locally at ~/.zana/sentinel_lite.db.
No Gateway or Docker required — fully offline and sovereign.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sentinel_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL DEFAULT (datetime('now')),
    event_type   TEXT NOT NULL,
    payload_hash TEXT DEFAULT '',
    civic_hash   TEXT DEFAULT '',
    aeon_id      TEXT DEFAULT ''
);
"""


class SentinelLiteDB:
    """SQLite ring-buffer for ZANA Sentinel events (SPROUT / offline tier).

    Keeps the last MAX_EVENTS entries at ~/.zana/sentinel_lite.db.
    Oldest rows are pruned automatically after each insert so the file
    size stays bounded regardless of runtime duration.
    """

    DB_PATH = Path.home() / ".zana" / "sentinel_lite.db"
    MAX_EVENTS = 1000  # ring buffer size — oldest rows pruned beyond this

    def __init__(self) -> None:
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.DB_PATH))
        self._conn.row_factory = sqlite3.Row
        # WAL mode improves concurrent read performance
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._bootstrap()

    def _bootstrap(self) -> None:
        """Create the sentinel_events table if it does not exist."""
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        event_type: str,
        payload_hash: str = "",
        civic_hash: str = "",
        aeon_id: str = "",
    ) -> int:
        """Insert one sentinel event and prune oldest rows beyond MAX_EVENTS.

        Args:
            event_type:   Human-readable event category (e.g. "PreToolUse").
            payload_hash: Optional SHA-256 hex digest of the event payload.
            civic_hash:   Optional SHA-256 hex digest written to Civic Ledger.
            aeon_id:      Optional Aeon session identifier.

        Returns:
            The rowid of the newly inserted event.
        """
        cur = self._conn.execute(
            """
            INSERT INTO sentinel_events (event_type, payload_hash, civic_hash, aeon_id)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, payload_hash, civic_hash, aeon_id),
        )
        self._conn.commit()
        new_id: int = cur.lastrowid  # type: ignore[assignment]

        # Prune: keep only the last MAX_EVENTS rows (ring buffer behaviour)
        self._conn.execute(
            "DELETE FROM sentinel_events WHERE id NOT IN "
            "(SELECT id FROM sentinel_events ORDER BY id DESC LIMIT ?)",
            (self.MAX_EVENTS,),
        )
        self._conn.commit()

        return new_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def events(self, limit: int = 20, event_type: str | None = None) -> list[dict]:
        """Return the last *limit* events, most recent first.

        Args:
            limit:      Maximum number of rows to return.
            event_type: If provided, restrict results to this event type.

        Returns:
            List of dicts with keys: id, timestamp, event_type,
            payload_hash, civic_hash, aeon_id.
        """
        if event_type:
            rows = self._conn.execute(
                """
                SELECT id, timestamp, event_type, payload_hash, civic_hash, aeon_id
                FROM sentinel_events
                WHERE event_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (event_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, timestamp, event_type, payload_hash, civic_hash, aeon_id
                FROM sentinel_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def ledger(self, limit: int = 20) -> list[dict]:
        """Return the last *limit* Civic Ledger entries (events with a civic_hash).

        Args:
            limit: Maximum number of rows to return.

        Returns:
            List of dicts with keys: id, timestamp, event_type,
            payload_hash, civic_hash, aeon_id.
        """
        rows = self._conn.execute(
            """
            SELECT id, timestamp, event_type, payload_hash, civic_hash, aeon_id
            FROM sentinel_events
            WHERE civic_hash != ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict:
        """Return aggregate statistics for the local sentinel database.

        Returns:
            Dict with keys:
            - ``total``:   Total number of events stored.
            - ``by_type``: Mapping of event_type → count.
        """
        total_row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM sentinel_events"
        ).fetchone()
        total: int = total_row["cnt"] if total_row else 0

        type_rows = self._conn.execute(
            "SELECT event_type, COUNT(*) AS cnt FROM sentinel_events GROUP BY event_type"
        ).fetchall()
        by_type: dict[str, int] = {row["event_type"]: row["cnt"] for row in type_rows}

        return {"total": total, "by_type": by_type}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()


def get_sentinel_db() -> SentinelLiteDB:
    """Return a SentinelLiteDB instance, creating the DB file if needed."""
    return SentinelLiteDB()
