"""Shared async Redis client — singleton connection pool."""
from __future__ import annotations

import redis.asyncio as aioredis
import structlog

from acr.config import settings

logger = structlog.get_logger(__name__)

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Initialize the connection pool. Called once at app startup."""
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    # Verify connectivity
    await _redis.ping()
    logger.info("redis_connected", url=settings.redis_url)


async def close_redis() -> None:
    """Close the connection pool. Called at app shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    """Return the shared Redis client. Raises if not initialized."""
    if _redis is None:
        raise RuntimeError("Redis client not initialized — call init_redis() at startup")
    return _redis


def get_redis_or_none() -> aioredis.Redis | None:
    """Return the Redis client, or None if not initialized (for graceful degradation)."""
    return _redis
