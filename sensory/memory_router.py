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
PG_DB   = os.getenv("ZANA_PG_DB", "zana_episodic")
PG_USER = os.getenv("ZANA_PG_USER", "zana")
PG_PASS = os.getenv("ZANA_PG_PASSWORD", "")

CHROMA_URL = os.getenv("ZANA_CHROMA_URL", "http://localhost:58001")


# ── PostgreSQL async connection pool ─────────────────────────────────────────

_pool = None

async def _get_pool():
    global _pool
    if _pool is None:
        try:
            import asyncpg  # type: ignore
            _pool = await asyncpg.create_pool(
                host=PG_HOST, port=PG_PORT, database=PG_DB,
                user=PG_USER, password=PG_PASS,
                min_size=1, max_size=5,
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


# ── Chroma helpers ─────────────────────────────────────────────────────────

async def _chroma_stats() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{CHROMA_URL}/api/v1/collections")
            if r.status_code != 200:
                return {"status": "offline", "collections": [], "total_docs": 0}
            cols = r.json()
            total = 0
            for c in cols:
                try:
                    rc = await client.get(f"{CHROMA_URL}/api/v1/collections/{c['id']}/count")
                    total += rc.json() if rc.status_code == 200 else 0
                except Exception:
                    pass
            return {"status": "online", "collections": [c["name"] for c in cols], "total_docs": total}
    except Exception:
        return {"status": "offline", "collections": [], "total_docs": 0}


# ── Request models ────────────────────────────────────────────────────────────

class EpisodicRecord(BaseModel):
    session_id: str
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
):
    """Returns the most recent episodic memory records from PostgreSQL."""
    if session_id:
        rows = await _pg_fetch(
            """SELECT id, session_id, role, content, modality, emotion,
                      kalman_surprise, created_at
               FROM episodic_memory
               WHERE session_id = $1
               ORDER BY created_at DESC LIMIT $2""",
            session_id, limit,
        )
    else:
        rows = await _pg_fetch(
            """SELECT id, session_id, role, content, modality, emotion,
                      kalman_surprise, created_at
               FROM episodic_memory
               ORDER BY created_at DESC LIMIT $1""",
            limit,
        )

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
               (session_id, role, content, modality, emotion, kalman_surprise, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        rec.session_id, rec.role, rec.content, rec.modality,
        rec.emotion, rec.kalman_surprise,
        datetime.now(timezone.utc),
    )
    return {"stored": ok, "session_id": rec.session_id}


@router.get("/stats", summary="Collection sizes across all 4 memory stores")
async def memory_stats():
    """Aggregate statistics for the full 4-store memory system."""
    chroma = await _chroma_stats()

    # Episodic count
    ep_rows = await _pg_fetch("SELECT COUNT(*) AS cnt FROM episodic_memory")
    ep_count = ep_rows[0]["cnt"] if ep_rows else None

    pg_status = "online" if ep_count is not None else "offline"

    return {
        "stores": {
            "semantic": {
                "backend": "ChromaDB",
                "status": chroma["status"],
                "collections": chroma["collections"],
                "total_documents": chroma["total_docs"],
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
