import os
import json
import redis
import hashlib
from typing import Optional, Dict, Any


class SemanticCache:
    """
    ZANA Semantic Cache using Redis.
    Uses query hashing for exact/near-exact matches in Phase 5.
    Future: Use RediSearch for true vector similarity.
    """

    def __init__(self, redis_url: str = None, ttl: int = 3600):
        redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6380")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl

    def _get_key(self, query: str) -> str:
        h = hashlib.sha256(query.encode()).hexdigest()
        return f"cache:semantic:{h}"

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached response if it exists.
        """
        key = self._get_key(query)
        try:
            data = self.redis.get(key)
            if data:
                print(f"🌀 [CACHE HIT] Resonancia encontrada para '{query[:30]}...'")
                return json.loads(data)
            return None
        except Exception as e:
            print(f"❌ Cache error: {e}")
            return None

    def set(self, query: str, response: str, metadata: Dict[str, Any] = None):
        """Stores a response in the cache."""
        key = self._get_key(query)
        payload = {"response": response, "metadata": metadata or {}}
        try:
            self.redis.setex(key, self.ttl, json.dumps(payload))
        except Exception as e:
            print(f"❌ Cache store error: {e}")
