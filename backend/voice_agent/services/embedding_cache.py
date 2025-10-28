"""Embedding cache with Redis backend for fast retrieval."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

import redis

from ..core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client.
    
    Returns:
        Redis client or None if not configured
    """
    global _redis_client
    
    if not settings.redis_url:
        logger.warning("REDIS_URL not configured, caching disabled")
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.redis_url)
            _redis_client.ping()
            logger.info("✅ Redis cache initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    return _redis_client


def get_cache_key(text: str, prefix: str = "embedding") -> str:
    """Generate cache key from text.
    
    Args:
        text: Text to generate key for
        prefix: Cache key prefix
        
    Returns:
        Cache key (MD5 hash)
    """
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"{prefix}:{text_hash}"


def get_cached_embedding(text: str) -> Optional[list[float]]:
    """Get embedding from Redis cache.
    
    Args:
        text: Text to retrieve embedding for
        
    Returns:
        Embedding vector or None if not cached
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        cache_key = get_cache_key(text)
        cached = client.get(cache_key)
        
        if cached:
            embedding = json.loads(cached)
            logger.debug(f"✅ Cache hit for embedding (key: {cache_key[:20]}...)")
            return embedding
        
        return None
        
    except Exception as e:
        logger.warning(f"Redis cache get failed: {e}")
        return None


def cache_embedding(text: str, embedding: list[float]) -> bool:
    """Store embedding in Redis cache.
    
    Args:
        text: Original text
        embedding: Embedding vector to cache
        
    Returns:
        True if cached successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        cache_key = get_cache_key(text)
        embedding_json = json.dumps(embedding)
        
        # Store with TTL (default 24 hours)
        client.setex(
            cache_key,
            settings.embedding_cache_ttl,
            embedding_json
        )
        
        logger.debug(f"💾 Cached embedding (key: {cache_key[:20]}..., ttl: {settings.embedding_cache_ttl}s)")
        return True
        
    except Exception as e:
        logger.warning(f"Redis cache set failed: {e}")
        return False


def clear_embedding_cache() -> bool:
    """Clear all embedding cache entries.
    
    Returns:
        True if cleared successfully
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        # Get all embedding keys and delete them
        keys = client.keys("embedding:*")
        if keys:
            client.delete(*keys)
            logger.info(f"✅ Cleared {len(keys)} cached embeddings")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return False


def get_cache_stats() -> dict[str, any]:
    """Get Redis cache statistics.
    
    Returns:
        Dictionary with cache stats
    """
    client = get_redis_client()
    if not client:
        return {"status": "disabled"}
    
    try:
        info = client.info()
        keys = client.keys("embedding:*")
        
        return {
            "status": "enabled",
            "total_keys": len(keys) if keys else 0,
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected": True,
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"status": "error", "error": str(e)}


def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
            _redis_client = None
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

