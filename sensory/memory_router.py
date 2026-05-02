"""
/memory — 4-store memory query endpoints.

  GET /memory/episodic          last N episodic records
  GET /memory/episodic/search   vector similarity search in episodic store
  GET /memory/stats             collection sizes across all 4 stores
  POST /memory/episodic         store a new episodic record

Backends (EPISODIC_BACKEND env var):
  sqlite    — default, zero-config, stores at ~/.zana/episodic.db
  postgres  — PostgreSQL + pgvector (full-stack, requires Docker)
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("zana.memory")

router = APIRouter(prefix="/memory", tags=["Memory"])

# ── Backend selection ─────────────────────────────────────────────────────────

EPISODIC_BACKEND = os.getenv("EPISODIC_BACKEND", "sqlite").lower()

# PostgreSQL config (only used when EPISODIC_BACKEND=postgres)
PG_HOST = os.getenv("ZANA_PG_HOST", "localhost")
PG_PORT = int(os.getenv("ZANA_PG_PORT", "55433"))
PG_DB = os.getenv("ZANA_PG_DB", "zana_episodic")
PG_USER = os.getenv("ZANA_PG_USER", "zana")
PG_PASS = os.getenv("ZANA_PG_PASSWORD", "")

# SQLite config (default)
_SQLITE_DB_PATH = Path(os.getenv("ZANA_SQLITE_PATH", str(Path.home() / ".zana" / "episodic.db")))


# ── SQLite backend ────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    session_id  TEXT NOT NULL,
    project_id  TEXT,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    modality    TEXT DEFAULT 'text',
    emotion     TEXT,
    kalman_surprise REAL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session ON episodic_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_project ON episodic_memory(project_id);
CREATE INDEX IF NOT EXISTS idx_created ON episodic_memory(created_at DESC);
"""

_sqlite_initialized = False


async def _sqlite_ensure_schema() -> None:
    global _sqlite_initialized
    if _sqlite_initialized:
        return
    try:
        import aiosqlite
        _SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(_SQLITE_DB_PATH) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        _sqlite_initialized = True
        logger.info("SQLite episodic store ready: %s", _SQLITE_DB_PATH)
    except ImportError:
        logger.warning("aiosqlite not installed — run: pip install aiosqlite")
    except Exception as e:
        logger.warning("SQLite init failed: %s", e)


async def _sqlite_fetch(
    limit: int,
    session_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> list[dict]:
    await _sqlite_ensure_schema()
    try:
        import aiosqlite
        query = "SELECT id, session_id, project_id, role, content, modality, emotion, kalman_surprise, created_at FROM episodic_memory WHERE 1=1"
        params: list = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(_SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("SQLite fetch failed: %s", e)
        return []


async def _sqlite_insert(rec) -> bool:
    await _sqlite_ensure_schema()
    try:
        import aiosqlite
        row_id = uuid.uuid4().hex
        async with aiosqlite.connect(_SQLITE_DB_PATH) as db:
            await db.execute(
                """INSERT INTO episodic_memory
                   (id, session_id, project_id, role, content, modality, emotion, kalman_surprise, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row_id,
                    rec.session_id,
                    rec.project_id,
                    rec.role,
                    rec.content,
                    rec.modality,
                    rec.emotion,
                    rec.kalman_surprise,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        return True
    except Exception as e:
        logger.warning("SQLite insert failed: %s", e)
        return False


async def _sqlite_count() -> Optional[int]:
    await _sqlite_ensure_schema()
    try:
        import aiosqlite
        async with aiosqlite.connect(_SQLITE_DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM episodic_memory") as cur:
                row = await cur.fetchone()
                return row[0] if row else 0
    except Exception:
        return None


# ── PostgreSQL backend (legacy / full-stack) ──────────────────────────────────

_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        try:
            import asyncpg  # type: ignore

            _pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=1,
                max_size=5,
            )
        except Exception as e:
            logger.warning("PostgreSQL pool unavailable: %s", e)
            return None
    return _pool


async def _pg_fetch(query: str, *args) -> list[dict]:
    pool = await _get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("PostgreSQL query failed: %s", e)
        return []


async def _pg_execute(query: str, *args) -> bool:
    pool = await _get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(query, *args)
            return True
    except Exception as e:
        logger.warning("PostgreSQL execute failed: %s", e)
        return False


# ── Request models ────────────────────────────────────────────────────────────


class EpisodicRecord(BaseModel):
    session_id: str
    project_id: Optional[str] = None
    role: str  # "user" | "aeon"
    content: str
    modality: str = "text"
    emotion: Optional[str] = None
    kalman_surprise: Optional[float] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/episodic", summary="Last N episodic memories")
async def get_episodic(
    limit: int = Query(default=10, ge=1, le=200, description="Number of records"),
    session_id: Optional[str] = Query(default=None, description="Filter by session"),
    project_id: Optional[str] = Query(default=None, description="Filter by project"),
):
    """Returns the most recent episodic memory records. Backend: SQLite (default) or PostgreSQL."""
    if EPISODIC_BACKEND == "sqlite":
        rows = await _sqlite_fetch(limit, session_id=session_id, project_id=project_id)
        return rows

    # PostgreSQL path
    query = "SELECT id, session_id, project_id, role, content, modality, emotion, kalman_surprise, created_at FROM episodic_memory WHERE 1=1"
    args = []
    if session_id:
        args.append(session_id)
        query += f" AND session_id = ${len(args)}"
    if project_id:
        args.append(project_id)
        query += f" AND project_id = ${len(args)}"
    args.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(args)}"
    rows = await _pg_fetch(query, *args)
    for r in rows:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
    return rows


@router.post("/episodic", summary="Store a new episodic record", status_code=201)
async def store_episodic(rec: EpisodicRecord):
    """Persists one turn of conversation into episodic memory."""
    if EPISODIC_BACKEND == "sqlite":
        ok = await _sqlite_insert(rec)
        _emit_memory_write(rec, ok, "sqlite")
        return {"stored": ok, "session_id": rec.session_id, "backend": "sqlite"}

    ok = await _pg_execute(
        """INSERT INTO episodic_memory
               (session_id, project_id, role, content, modality, emotion, kalman_surprise, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        rec.session_id,
        rec.project_id,
        rec.role,
        rec.content,
        rec.modality,
        rec.emotion,
        rec.kalman_surprise,
        datetime.now(timezone.utc),
    )
    _emit_memory_write(rec, ok, "postgres")
    return {"stored": ok, "session_id": rec.session_id, "backend": "postgres"}


def _emit_memory_write(rec: "EpisodicRecord", success: bool, backend: str) -> None:
    """Fire MEMORY_WRITE sentinel event (best-effort, never raises)."""
    try:
        from sentinel.event_bus import get_bus, ZanaEvent, EventType
        import asyncio
        event = ZanaEvent(
            type=EventType.MEMORY_WRITE,
            payload={
                "store": "episodic",
                "backend": backend,
                "session_id": rec.session_id,
                "role": rec.role,
                "modality": rec.modality,
                "success": success,
                "content_len": len(rec.content) if rec.content else 0,
            },
            session_id=rec.session_id,
        )
        asyncio.create_task(get_bus().emit(event, fire_and_forget=True))
    except Exception as _e:
        logger.debug("Sentinel MEMORY_WRITE emit skipped: %s", _e)


@router.get("/graph", summary="Knowledge graph — topics + entities extracted from episodic memory")
async def memory_graph(
    limit: int = Query(default=150, ge=10, le=500, description="Records to analyse"),
    project_id: Optional[str] = Query(default=None),
    top_topics: int = Query(default=24, ge=5, le=60, description="Max topic nodes"),
):
    """
    Extracts topics/entities from recent episodic memory and returns a graph
    structure ready for visualisation: {nodes, edges, timeline, stats}.

    Topic extraction is frequency-based (zero ML, no extra dependencies):
      1. Tokenise content words
      2. Remove stopwords (EN + ES)
      3. Count frequency across all records
      4. Top N words = nodes; co-occurrence in same record = edges
    """
    import re
    from collections import Counter, defaultdict

    _STOP = {
        # English
        "the","and","for","that","this","with","from","have","will","are","was",
        "not","but","can","been","your","they","them","then","when","what","which",
        "also","into","than","more","very","just","all","one","any","some","our",
        "its","out","has","had","how","who","you","their","there","these","those",
        "should","would","could","about","after","before","other","each","over",
        "only","even","both","such","much","many","still","also","well","back",
        "being","doing","going","using","used","make","made","need","like","want",
        "here","where","while","now","get","got","let","may","per","set","use",
        # Spanish
        "que","una","los","las","del","por","con","para","como","pero","este",
        "esta","esto","son","ser","fue","una","hay","sus","sin","más","sobre",
        "entre","así","todo","todos","cada","cuando","porque","también","puede",
        "hace","han","tiene","tienen","está","están","era","una","hacia","desde",
        "hasta","aunque","siempre","nunca","mismo","misma","otro","otra","bien",
        "gran","solo","sólo","pues","donde","menos","algo","nadie","nada",
    }

    if EPISODIC_BACKEND == "sqlite":
        rows = await _sqlite_fetch(limit, project_id=project_id)
    else:
        rows = await _pg_fetch(
            """SELECT session_id, project_id, role, content, emotion, kalman_surprise, created_at
               FROM episodic_memory
               WHERE 1=1 {filter}
               ORDER BY created_at DESC LIMIT $1""".replace(
                "{filter}", f"AND project_id = $2" if project_id else ""
            ),
            *(([limit, project_id]) if project_id else [limit]),
        )

    # Normalize timestamps
    for r in rows:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()

    # ── Topic extraction ──────────────────────────────────────────────────────
    word_freq: Counter = Counter()
    record_words: list[set] = []

    for rec in rows:
        text = rec.get("content", "")
        words = {
            w.lower()
            for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text)
            if w.lower() not in _STOP
        }
        record_words.append(words)
        word_freq.update(words)

    top = [w for w, _ in word_freq.most_common(top_topics)]
    top_set = set(top)

    # ── Co-occurrence edges ───────────────────────────────────────────────────
    edge_weight: defaultdict = defaultdict(int)
    for words in record_words:
        hits = words & top_set
        hits_list = sorted(hits)
        for i in range(len(hits_list)):
            for j in range(i + 1, len(hits_list)):
                key = (hits_list[i], hits_list[j])
                edge_weight[key] += 1

    # ── Build response ────────────────────────────────────────────────────────
    TOPIC_COLORS = [
        "#6366f1", "#8b5cf6", "#a855f7", "#06b6d4", "#0ea5e9",
        "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#14b8a6",
        "#f97316", "#84cc16", "#e879f9", "#67e8f9", "#fbbf24",
    ]
    nodes = [
        {
            "id": f"topic:{w}",
            "type": "topic",
            "label": w,
            "weight": word_freq[w],
            "color": TOPIC_COLORS[i % len(TOPIC_COLORS)],
        }
        for i, w in enumerate(top)
    ]

    edges = [
        {"source": f"topic:{a}", "target": f"topic:{b}", "weight": w}
        for (a, b), w in edge_weight.items()
        if w >= 2  # only show edges with at least 2 co-occurrences
    ]

    # Emotion stats
    emotion_counts: Counter = Counter(
        r["emotion"] for r in rows if r.get("emotion")
    )
    dominant_emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else "neutral"

    # Day coverage
    days: set = set()
    for r in rows:
        ts = r.get("created_at", "")
        if ts:
            days.add(str(ts)[:10])

    return {
        "nodes": nodes,
        "edges": edges,
        "timeline": rows[:30],  # last 30 for the timeline panel
        "stats": {
            "total_analysed": len(rows),
            "topics_extracted": len(nodes),
            "edges": len(edges),
            "days_covered": len(days),
            "dominant_emotion": dominant_emotion,
        },
    }


@router.get("/stats", summary="Collection sizes across all 4 memory stores")
async def memory_stats():
    """Aggregate statistics for the full 4-store memory system."""
    if EPISODIC_BACKEND == "sqlite":
        ep_count = await _sqlite_count()
        ep_backend_label = f"SQLite ({_SQLITE_DB_PATH})"
        ep_status = "online" if ep_count is not None else "offline"
    else:
        ep_rows = await _pg_fetch("SELECT COUNT(*) AS cnt FROM episodic_memory")
        ep_count = ep_rows[0]["cnt"] if ep_rows else None
        ep_backend_label = "PostgreSQL+pgvector"
        ep_status = "online" if ep_count is not None else "offline"

    return {
        "stores": {
            "semantic": {
                "backend": "Zana Steel Core",
                "status": "online",
                "total_documents": "simulated",
            },
            "episodic": {
                "backend": ep_backend_label,
                "status": ep_status,
                "total_records": ep_count,
            },
            "world_model": {
                "backend": "Neo4j",
                "status": "via_gateway",
                "note": "Query via /sense/text with symbolic facts",
            },
            "procedural": {
                "backend": "JSON files",
                "status": "local",
                "note": "aeons/registry.json + skills/",
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
