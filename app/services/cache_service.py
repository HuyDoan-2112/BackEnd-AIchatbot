"""
Redis-based caching service for chat responses.
Optimizes performance by caching repeated/similar queries.
"""
import json
import hashlib
import logging
from typing import Optional, Any, Dict
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based cache for chat completions and other data."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[aioredis.Redis] = None
        self._enabled = self.settings.ENABLE_RESPONSE_CACHE

    async def connect(self):
        """Initialize Redis connection pool."""
        if not self._enabled:
            logger.info("Cache service disabled by configuration")
            return

        try:
            self._redis = await aioredis.from_url(
                f"redis://{self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}/{self.settings.REDIS_DB}",
                password=self.settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            await self._redis.ping()
            logger.info(f"Redis cache connected: {self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}")
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            self._redis = None
            self._enabled = False

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis cache disconnected")

    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate a cache key from request data."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True)
        hash_digest = hashlib.sha256(sorted_data.encode()).hexdigest()
        return f"{prefix}:{hash_digest[:16]}"

    async def get(self, key: str) -> Optional[str]:
        """Retrieve cached value."""
        if not self._enabled or not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
            return value
        except RedisError as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Store value in cache with optional TTL."""
        if not self._enabled or not self._redis:
            return False

        try:
            ttl = ttl or self.settings.REDIS_CACHE_TTL
            await self._redis.setex(key, ttl, value)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except RedisError as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        if not self._enabled or not self._redis:
            return False

        try:
            await self._redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self._enabled or not self._redis:
            return 0

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache CLEAR: {deleted} keys matching '{pattern}'")
                return deleted
            return 0
        except RedisError as e:
            logger.warning(f"Cache clear error: {e}")
            return 0

    def generate_chat_cache_key(
        self,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate cache key for chat completion requests."""
        # Only cache based on recent messages to avoid over-caching
        recent_messages = messages[-3:] if len(messages) > 3 else messages

        cache_data = {
            "model": model,
            "messages": [
                {"role": msg.get("role"), "content": msg.get("content", "")[:200]}  # Limit content length
                for msg in recent_messages
            ],
            "temperature": round(temperature, 2),
            "max_tokens": max_tokens
        }

        return self._generate_cache_key("chat", cache_data)

    async def get_chat_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached chat response."""
        cached_value = await self.get(cache_key)
        if cached_value:
            try:
                return json.loads(cached_value)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode cached response: {e}")
                return None
        return None

    async def set_chat_response(
        self,
        cache_key: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store chat response in cache."""
        try:
            json_value = json.dumps(response)
            return await self.set(cache_key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize response: {e}")
            return False


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the singleton cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
