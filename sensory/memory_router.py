"""
/memory — 4-store memory query endpoints.

  GET /memory/episodic          last N episodic records (PostgreSQL+pgvector)
  GET /memory/episodic/search   vector similarity search in episodic store
  GET /memory/stats             collection sizes across all 4 stores
  POST /memory/episodic         store a new episodic record
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger("zana.memory")

router = APIRouter(prefix="/memory", tags=["Memory"])

PG_HOST = os.getenv("ZANA_PG_HOST", "localhost")
PG_PORT = int(os.getenv("ZANA_PG_PORT", "55433"))
PG_DB = os.getenv("ZANA_PG_DB", "zana_episodic")
PG_USER = os.getenv("ZANA_PG_USER", "zana")
PG_PASS = os.getenv("ZANA_PG_PASSWORD", "")


# ── PostgreSQL async connection pool ─────────────────────────────────────────

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
    """Returns the most recent episodic memory records from PostgreSQL."""
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

    # Normalize timestamps for JSON
    for r in rows:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()

    return rows


@router.post("/episodic", summary="Store a new episodic record", status_code=201)
async def store_episodic(rec: EpisodicRecord):
    """Persists one turn of conversation into episodic memory."""
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
    return {"stored": ok, "session_id": rec.session_id}


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
    # Episodic count
    ep_rows = await _pg_fetch("SELECT COUNT(*) AS cnt FROM episodic_memory")
    ep_count = ep_rows[0]["cnt"] if ep_rows else None

    pg_status = "online" if ep_count is not None else "offline"

    return {
        "stores": {
            "semantic": {
                "backend": "Zana Steel Core",
                "status": "online",
                "total_documents": "simulated",
            },
            "episodic": {
                "backend": "PostgreSQL+pgvector",
                "status": pg_status,
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
