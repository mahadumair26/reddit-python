"""Async Redis cache utilities."""

import json
from typing import Any, Optional

from redis import asyncio as aioredis

from src.config.settings import settings
from src.utils.logger import logger


class RedisCache:
    """Async Redis cache manager."""

    def __init__(self) -> None:
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis if available."""
        try:
            self.redis = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info("Redis connection established")
        except Exception as exc:  # pragma: no cover - depends on external service
            logger.warning("Redis unavailable, running without cache: %s", exc)
            self.redis = None

    async def disconnect(self) -> None:
        """Close Redis client."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as exc:
            logger.error("Cache get error for key %s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as exc:
            logger.error("Cache set error for key %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as exc:
            logger.error("Cache delete error for key %s: %s", key, exc)
            return False


cache = RedisCache()
