"""
Resilient async HTTP client for ZANA Gateway — v3.0.

Improvements over v2.0:
- Typed exceptions (GatewayDown, GatewayTimeout, GatewayError)
- Retry with exponential backoff (3 attempts: 0s → 1s → 3s)
- Circuit breaker (5 consecutive failures → 30s open window)
- Timeout tiers: LLM calls 90s, control calls 10s, default 30s
- All callers see clean exceptions, never raw httpx internals
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger("zana.telegram.gw")

GATEWAY_URL = os.getenv("ZANA_GATEWAY_URL", "http://localhost:54446")

# ── Typed exceptions ──────────────────────────────────────────────────────────

class GatewayError(Exception):
    """Base class for gateway errors."""

class GatewayDown(GatewayError):
    """Gateway is unreachable or returning 5xx."""

class GatewayTimeout(GatewayError):
    """Request timed out."""

class GatewayRejected(GatewayError):
    """Gateway returned 4xx (bad request, not found, etc.)."""


# ── Circuit Breaker ───────────────────────────────────────────────────────────

class _CircuitBreaker:
    """Simple async circuit breaker — opens after N failures, resets after cooldown."""

    def __init__(self, failure_threshold: int = 5, cooldown_s: float = 30.0):
        self._failures = 0
        self._threshold = failure_threshold
        self._cooldown = cooldown_s
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self._cooldown:
            self._opened_at = None
            self._failures = 0
            logger.info("Circuit breaker reset after cooldown")
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            if self._opened_at is None:
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit breaker OPEN after %d failures — gateway unreachable",
                    self._failures,
                )

    def remaining_cooldown(self) -> float:
        if self._opened_at is None:
            return 0.0
        return max(0.0, self._cooldown - (time.monotonic() - self._opened_at))


_cb = _CircuitBreaker()

# ── Timeout tiers ─────────────────────────────────────────────────────────────

_T_LLM     = httpx.Timeout(90.0, connect=5.0)   # sense_text/audio/vision → LLM
_T_CONTROL = httpx.Timeout(10.0, connect=5.0)   # status, lists, quick ops
_T_MINING  = httpx.Timeout(120.0, connect=5.0)  # wisdom/mine → LLM batch


# ── Core request helper ───────────────────────────────────────────────────────

async def _request(
    method: str,
    path: str,
    *,
    timeout: httpx.Timeout = _T_CONTROL,
    retries: int = 3,
    **kwargs: Any,
) -> dict | list:
    """
    Retry wrapper with circuit breaker.
    Raises typed exceptions on final failure.
    """
    if _cb.is_open():
        remaining = _cb.remaining_cooldown()
        raise GatewayDown(
            f"Circuit breaker open — gateway unreachable. "
            f"Retry in {remaining:.0f}s."
        )

    url = f"{GATEWAY_URL}{path}"
    last_exc: Exception | None = None

    for attempt in range(retries):
        if attempt > 0:
            await asyncio.sleep(2 ** (attempt - 1))  # 0s, 1s, 3s

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, **kwargs)

            if response.status_code >= 500:
                _cb.record_failure()
                raise GatewayDown(f"Gateway {response.status_code}: {response.text[:200]}")

            if response.status_code >= 400:
                raise GatewayRejected(f"Gateway {response.status_code}: {response.text[:200]}")

            _cb.record_success()
            return response.json()

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            _cb.record_failure()
            last_exc = GatewayDown(f"Cannot reach gateway at {GATEWAY_URL}: {e}")
        except httpx.TimeoutException as e:
            last_exc = GatewayTimeout(f"Request timed out: {e}")
        except (GatewayDown, GatewayRejected):
            raise
        except Exception as e:
            last_exc = GatewayError(f"Unexpected error: {e}")

        logger.warning("Gateway attempt %d/%d failed: %s", attempt + 1, retries, last_exc)

    raise last_exc or GatewayError("All retries exhausted")


# ── API surface ───────────────────────────────────────────────────────────────

async def sense_text(text: str, session_id: str) -> dict:
    return await _request(
        "POST", "/sense/text",
        timeout=_T_LLM,
        json={"text": text, "session_id": session_id, "respond_with_audio": False},
    )


async def sense_audio(audio_bytes: bytes, mime: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=_T_LLM) as c:
        if _cb.is_open():
            raise GatewayDown("Circuit breaker open")
        try:
            r = await c.post(
                f"{GATEWAY_URL}/sense/audio",
                files={"audio": ("voice.ogg", audio_bytes, mime)},
                data={"session_id": session_id, "respond_with_audio": "true"},
            )
            r.raise_for_status()
            _cb.record_success()
            return r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            _cb.record_failure()
            raise GatewayDown(str(e))
        except httpx.TimeoutException as e:
            raise GatewayTimeout(str(e))


async def sense_vision(image_bytes: bytes, mime: str, session_id: str, hint: str = "") -> dict:
    async with httpx.AsyncClient(timeout=_T_LLM) as c:
        if _cb.is_open():
            raise GatewayDown("Circuit breaker open")
        try:
            r = await c.post(
                f"{GATEWAY_URL}/sense/vision",
                files={"media": ("image.jpg", image_bytes, mime)},
                data={"session_id": session_id, "context_hint": hint},
            )
            r.raise_for_status()
            _cb.record_success()
            return r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            _cb.record_failure()
            raise GatewayDown(str(e))
        except httpx.TimeoutException as e:
            raise GatewayTimeout(str(e))


async def sense_document(text_content: str, filename: str, session_id: str) -> dict:
    return await _request(
        "POST", "/sense/text",
        timeout=_T_LLM,
        json={
            "text": f"[Documento adjunto: {filename}]\n\n{text_content}",
            "session_id": session_id,
            "respond_with_audio": False,
        },
    )


async def reason(fact_raw: str, session_id: str, remote: bool = False) -> dict:
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
    return await _request(
        "POST", "/reason",
        timeout=_T_LLM,
        json={"fact": fact, "remote_query": remote},
    )


async def memory_recall(n: int = 10, session_id: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"limit": n}
    if session_id:
        params["session_id"] = session_id
    result = await _request("GET", "/memory/episodic", timeout=_T_CONTROL, params=params)
    return result if isinstance(result, list) else []


async def memory_search(query: str, collection: str = "zana_vault", n: int = 5) -> dict:
    result = await _request(
        "POST", "/memory/search",
        timeout=_T_CONTROL,
        json={"query": query, "collection": collection, "n_results": n},
    )
    return result if isinstance(result, dict) else {}


async def health() -> dict:
    result = await _request("GET", "/health", timeout=_T_CONTROL, retries=1)
    return result if isinstance(result, dict) else {}


async def swarm_status() -> dict:
    result = await _request("GET", "/swarm/status", timeout=_T_CONTROL, retries=1)
    return result if isinstance(result, dict) else {}


async def wisdom_inbox() -> dict:
    result = await _request("GET", "/wisdom/inbox", timeout=_T_CONTROL)
    return result if isinstance(result, dict) else {}


async def wisdom_approve(wisdom_id: str) -> dict:
    result = await _request("POST", f"/wisdom/approve/{wisdom_id}", timeout=_T_CONTROL, json={})
    return result if isinstance(result, dict) else {}


async def wisdom_reject(wisdom_id: str) -> dict:
    result = await _request("POST", f"/wisdom/reject/{wisdom_id}", timeout=_T_CONTROL)
    return result if isinstance(result, dict) else {}


async def wisdom_mine() -> dict:
    result = await _request("POST", "/wisdom/mine", timeout=_T_MINING, retries=1)
    return result if isinstance(result, dict) else {}


async def sentinel_status() -> dict:
    result = await _request("GET", "/sentinel/status", timeout=_T_CONTROL, retries=1)
    return result if isinstance(result, dict) else {}


async def aeon_list() -> list[dict]:
    import json
    from pathlib import Path
    p = Path(__file__).parent
    for _ in range(6):
        candidate = p / "aeons" / "registry.json"
        if candidate.exists():
            return json.loads(candidate.read_text()).get("aeons", [])
        p = p.parent
    return []
