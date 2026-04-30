"""
WebSearchTool + BrowseUrlTool for the OPERATOR agent.

Provider priority (first available wins):
  1. Tavily  — set TAVILY_API_KEY  (RAG-optimized, privacy-first, ideal for AI agents)
  2. SearXNG — set SEARXNG_URL     (self-hosted sovereign search, zero cloud dependency)
  3. DuckDuckGo Instant Answers    (no API key needed, always available as fallback)
"""

from __future__ import annotations

import html as _html_module
import logging
import os
import re
from typing import Any

import httpx
from smolagents import Tool

logger = logging.getLogger("zana.web_tools")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "").rstrip("/")
_USER_AGENT = "ZANA/2.9 (sovereign AI agent; +https://github.com/Kemquiros/zana-core)"


# ── HTML → plaintext ──────────────────────────────────────────────────────────


def _strip_html(raw: str, max_chars: int = 4000) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = _html_module.unescape(text)
    return text[:max_chars]


# ── Per-provider search implementations ──────────────────────────────────────


def _search_tavily(query: str, num_results: int) -> list[dict]:
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": num_results,
                "search_depth": "basic",
                "include_answer": True,
            },
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        results: list[dict] = []
        if data.get("answer"):
            results.append({"title": "Direct Answer", "url": "", "snippet": data["answer"]})
        for r in data.get("results", [])[:num_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:600],
            })
        return results
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []


def _search_searxng(query: str, num_results: int) -> list[dict]:
    try:
        resp = httpx.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "language": "auto", "safesearch": "0"},
            headers={"User-Agent": _USER_AGENT},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:600],
            }
            for r in data.get("results", [])[:num_results]
        ]
    except Exception as exc:
        logger.warning("SearXNG search failed: %s", exc)
        return []


def _search_ddg(query: str, num_results: int) -> list[dict]:
    """DuckDuckGo Zero-Click Info API — no API key required."""
    try:
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1", "no_html": "1"},
            headers={"User-Agent": _USER_AGENT},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results: list[dict] = []
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", "DuckDuckGo"),
                "url": data.get("AbstractURL", ""),
                "snippet": data["AbstractText"][:600],
            })
        for topic in data.get("RelatedTopics", []):
            if len(results) >= num_results:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic["Text"][:80],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic["Text"][:600],
                })
        return results
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []


# ── Public helpers (used by both Tools and search_router) ─────────────────────


def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web via the first available provider."""
    if TAVILY_API_KEY:
        results = _search_tavily(query, num_results)
        if results:
            return results
    if SEARXNG_URL:
        results = _search_searxng(query, num_results)
        if results:
            return results
    return _search_ddg(query, num_results)


def browse_url(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return clean plaintext (strips HTML)."""
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "html" in ct:
            return _strip_html(resp.text, max_chars)
        return resp.text[:max_chars]
    except Exception as exc:
        return f"[browse_error: {exc}]"


def active_provider() -> str:
    if TAVILY_API_KEY:
        return "tavily"
    if SEARXNG_URL:
        return "searxng"
    return "duckduckgo"


# ── smolagents Tool wrappers ──────────────────────────────────────────────────


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web for current information: news, prices, events, facts, or any "
        "query requiring knowledge beyond the training cutoff. "
        "Returns a numbered list with title, URL, and content snippet for each result."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (1-10, default 5).",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, query: str, num_results: Any = 5) -> str:
        n = min(int(num_results or 5), 10)
        results = web_search(query, n)
        if not results:
            return f"[No results found for: {query!r}]"
        lines = [f"[Provider: {active_provider()}] Results for: {query!r}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            if r["url"]:
                lines.append(f"   {r['url']}")
            lines.append(f"   {r['snippet']}\n")
        return "\n".join(lines)


class BrowseUrlTool(Tool):
    name = "browse_url"
    description = (
        "Fetch the full text content of a URL. Use after web_search when you need "
        "to read the complete article or page (not just the snippet)."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "The URL to fetch.",
        }
    }
    output_type = "string"

    def forward(self, url: str) -> str:
        return browse_url(url)
