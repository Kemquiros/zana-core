"""
Per-user token bucket rate limiter for the Telegram Herald.

Default: 10 messages / 60 seconds per user_id.
Admins (ZANA_TELEGRAM_ALLOWED_USERS) get 3× the bucket.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    capacity: float
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)
    rate: float = 0.0           # tokens per second

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> float:
        """Seconds until next token is available."""
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.rate if self.rate > 0 else 60.0


class RateLimiter:
    """
    Token bucket limiter, one bucket per user_id.
    Thread-safe for asyncio (single-threaded event loop).
    """

    def __init__(
        self,
        messages_per_minute: int = 10,
        burst_multiplier: float = 1.5,
        admin_multiplier: float = 3.0,
        admin_ids: set[str] | None = None,
    ):
        self._rate = messages_per_minute / 60.0
        self._capacity = messages_per_minute * burst_multiplier
        self._admin_capacity = messages_per_minute * admin_multiplier
        self._admin_ids = admin_ids or set()
        self._buckets: dict[str, _Bucket] = defaultdict(self._make_bucket)

    def _make_bucket(self) -> _Bucket:
        return _Bucket(capacity=self._capacity, tokens=self._capacity, rate=self._rate)

    def _get_bucket(self, user_id: str) -> _Bucket:
        if user_id not in self._buckets:
            cap = self._admin_capacity if user_id in self._admin_ids else self._capacity
            self._buckets[user_id] = _Bucket(capacity=cap, tokens=cap, rate=self._rate)
        return self._buckets[user_id]

    def check(self, user_id: str | int) -> tuple[bool, float]:
        """
        Returns (allowed: bool, retry_after_seconds: float).
        Call this before processing a message.
        """
        bucket = self._get_bucket(str(user_id))
        allowed = bucket.consume()
        retry_after = 0.0 if allowed else bucket.retry_after()
        return allowed, retry_after
