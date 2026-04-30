"""
/search — Web search and URL browse endpoints.

  POST /search         search the web (Tavily → SearXNG → DuckDuckGo)
  POST /search/browse  fetch + extract text from a URL
  GET  /search/config  show active provider and configuration
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("zana.search")

router = APIRouter(prefix="/search", tags=["Search"])

# Resolve swarm module (sensory runs as a sub-process of the stack root)
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from swarm.apex.web_tools import web_search, browse_url, active_provider


# ── Request models ────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str
    num_results: int = 5


class BrowseRequest(BaseModel):
    url: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", summary="Search the web")
async def search(req: SearchRequest):
    """
    Search using the best available provider in priority order:
    Tavily (TAVILY_API_KEY set) → SearXNG (SEARXNG_URL set) → DuckDuckGo (always).

    Returns a list of {title, url, snippet} objects.
    """
    results = web_search(req.query, min(req.num_results, 10))
    return {
        "query": req.query,
        "results": results,
        "count": len(results),
        "provider": active_provider(),
    }


@router.post("/browse", summary="Fetch and extract text from a URL")
async def browse(req: BrowseRequest):
    """
    Fetches a URL and returns its content as clean plaintext (HTML stripped).
    Useful when you need the full article, not just a search snippet.
    """
    content = browse_url(req.url)
    return {
        "url": req.url,
        "content": content,
        "length": len(content),
    }


@router.get("/config", summary="Show active search provider and configuration")
async def search_config():
    """Returns which provider is active and what env vars are configured."""
    import os
    return {
        "active_provider": active_provider(),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "searxng_url": os.getenv("SEARXNG_URL", ""),
        "fallback": "duckduckgo",
        "note": "Set TAVILY_API_KEY for best results, or SEARXNG_URL for sovereign local search.",
    }
