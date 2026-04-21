"""
Async HTTP client for ZANA Gateway.
All bot handlers use this — never call the gateway directly from handlers.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

GATEWAY_URL = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")
_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


async def sense_text(text: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(f"{GATEWAY_URL}/sense/text",
                         json={"text": text, "session_id": session_id, "respond_with_audio": False})
        r.raise_for_status()
        return r.json()


async def sense_audio(audio_bytes: bytes, mime: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{GATEWAY_URL}/sense/audio",
            files={"audio": ("voice.ogg", audio_bytes, mime)},
            data={"session_id": session_id, "respond_with_audio": "true"},
        )
        r.raise_for_status()
        return r.json()


async def sense_vision(image_bytes: bytes, mime: str, session_id: str, hint: str = "") -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{GATEWAY_URL}/sense/vision",
            files={"media": ("image.jpg", image_bytes, mime)},
            data={"session_id": session_id, "context_hint": hint},
        )
        r.raise_for_status()
        return r.json()


async def reason(fact_raw: str, session_id: str, remote: bool = False) -> dict:
    # Parse "key=value" or raw JSON
    import json as _json
    fact_raw = fact_raw.strip()
    if fact_raw.startswith("{"):
        fact = _json.loads(fact_raw)
    elif "=" in fact_raw:
        k, _, v = fact_raw.partition("=")
        try:
            parsed = _json.loads(v)
        except Exception:
            parsed = v
        fact = {"fact_key": k.strip(), "value": parsed}
    else:
        fact = {"fact_key": fact_raw}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(f"{GATEWAY_URL}/reason",
                         json={"fact": fact, "remote_query": remote})
        r.raise_for_status()
        return r.json()


async def memory_recall(n: int = 10, session_id: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"limit": n}
    if session_id:
        params["session_id"] = session_id
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{GATEWAY_URL}/memory/episodic", params=params)
        r.raise_for_status()
        return r.json()


async def memory_search(query: str, collection: str = "zana_vault", n: int = 5) -> dict:
    """Semantic search — routed through Gateway's Chroma proxy if available."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{GATEWAY_URL}/memory/search",
            json={"query": query, "collection": collection, "n_results": n},
        )
        if r.status_code == 404:
            return {"error": "semantic_search_not_available"}
        r.raise_for_status()
        return r.json()


async def health() -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as c:
        r = await c.get(f"{GATEWAY_URL}/health")
        r.raise_for_status()
        return r.json()


async def swarm_status() -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as c:
        r = await c.get(f"{GATEWAY_URL}/swarm/status")
        r.raise_for_status()
        return r.json()


async def aeon_list() -> list[dict]:
    """Read Aeon registry directly from file (no Gateway route needed)."""
    import json
    from pathlib import Path
    # Walk up from this file to find aeons/registry.json
    p = Path(__file__).parent
    for _ in range(6):
        candidate = p / "aeons" / "registry.json"
        if candidate.exists():
            return json.loads(candidate.read_text()).get("aeons", [])
        p = p.parent
    return []
