"""
cache.py - Unified caching layer for ChatOS.

Provides multi-tier caching with:
- In-memory LRU cache for hot data
- Optional Redis integration for distributed caching
- TTL-based expiration
- Cache invalidation strategies

Usage:
    from chatos_backend.controllers.cache import get_cache, cache_key
    
    cache = get_cache()
    
    # Simple caching
    result = cache.get("my_key")
    if result is None:
        result = expensive_operation()
        cache.set("my_key", result, ttl=300)
    
    # Decorator usage
    @cache.cached(ttl=300, prefix="rag")
    async def get_rag_results(query: str):
        return await rag_engine.retrieve(query)
"""

import asyncio
import hashlib
import json
import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Configuration
# =============================================================================

class CacheTier(Enum):
    """Cache tier levels."""
    MEMORY = "memory"      # In-memory LRU cache
    REDIS = "redis"        # Redis distributed cache
    HYBRID = "hybrid"      # Both memory and Redis


@dataclass
class CacheConfig:
    """Configuration for the cache system."""
    # Memory cache settings
    memory_maxsize: int = 1000
    memory_default_ttl: float = 300.0  # 5 minutes
    
    # Redis settings (optional)
    redis_url: Optional[str] = None
    redis_default_ttl: float = 3600.0  # 1 hour
    redis_prefix: str = "chatos:"
    
    # Behavior settings
    tier: CacheTier = CacheTier.MEMORY
    enable_stats: bool = True
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create config from environment variables."""
        redis_url = os.environ.get("CHATOS_REDIS_URL")
        tier = CacheTier.HYBRID if redis_url else CacheTier.MEMORY
        
        return cls(
            memory_maxsize=int(os.environ.get("CHATOS_CACHE_MAXSIZE", "1000")),
            memory_default_ttl=float(os.environ.get("CHATOS_CACHE_TTL", "300")),
            redis_url=redis_url,
            redis_prefix=os.environ.get("CHATOS_REDIS_PREFIX", "chatos:"),
            tier=tier,
        )


# =============================================================================
# Cache Entry
# =============================================================================

@dataclass
class CacheEntry:
    """A cached value with metadata."""
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: float = 300.0
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """Get entry age in seconds."""
        return time.time() - self.created_at
    
    @property
    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.ttl - self.age)


# =============================================================================
# Memory Cache (LRU with TTL)
# =============================================================================

class MemoryCache:
    """
    In-memory LRU cache with TTL support.
    
    Thread-safe using asyncio locks.
    """
    
    def __init__(self, maxsize: int = 1000, default_ttl: float = 300.0):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired:
                    entry.hits += 1
                    self._hits += 1
                    # Move to end (most recently used)
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return entry.value
                else:
                    # Expired, remove
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
            
            self._misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Set a value in cache."""
        async with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self.maxsize and self._access_order:
                oldest_key = self._access_order.pop(0)
                self._cache.pop(oldest_key, None)
            
            entry = CacheEntry(
                value=value,
                ttl=ttl if ttl is not None else self.default_ttl,
            )
            self._cache[key] = entry
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> int:
        """Clear all entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            return count
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "type": "memory",
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "default_ttl": self.default_ttl,
        }


# =============================================================================
# Redis Cache (Optional)
# =============================================================================

class RedisCache:
    """
    Redis-backed cache for distributed caching.
    
    Falls back gracefully if Redis is unavailable.
    """
    
    def __init__(
        self,
        redis_url: str,
        default_ttl: float = 3600.0,
        prefix: str = "chatos:",
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._client = None
        self._available = False
        self._hits = 0
        self._misses = 0
    
    async def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self.redis_url)
                # Test connection
                await self._client.ping()
                self._available = True
                logger.info("Redis cache connected")
            except ImportError:
                logger.warning("redis package not installed, Redis cache disabled")
                self._available = False
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._available = False
        return self._client if self._available else None
    
    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        client = await self._get_client()
        if not client:
            return None
        
        try:
            redis_key = self._make_key(key)
            data = await client.get(redis_key)
            if data:
                self._hits += 1
                return json.loads(data)
            self._misses += 1
            return None
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            self._misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Set a value in Redis."""
        client = await self._get_client()
        if not client:
            return
        
        try:
            redis_key = self._make_key(key)
            ttl_seconds = int(ttl if ttl is not None else self.default_ttl)
            await client.setex(redis_key, ttl_seconds, json.dumps(value))
        except Exception as e:
            logger.debug(f"Redis set error: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            redis_key = self._make_key(key)
            result = await client.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.debug(f"Redis delete error: {e}")
            return False
    
    async def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern."""
        client = await self._get_client()
        if not client:
            return 0
        
        try:
            full_pattern = f"{self.prefix}{pattern}"
            keys = await client.keys(full_pattern)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.debug(f"Redis clear error: {e}")
            return 0
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "type": "redis",
            "available": self._available,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "default_ttl": self.default_ttl,
        }


# =============================================================================
# Unified Cache
# =============================================================================

class UnifiedCache:
    """
    Unified cache interface supporting multiple tiers.
    
    Provides a simple interface for caching with automatic
    tier selection and fallback.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig.from_env()
        
        # Initialize memory cache (always available)
        self._memory = MemoryCache(
            maxsize=self.config.memory_maxsize,
            default_ttl=self.config.memory_default_ttl,
        )
        
        # Initialize Redis cache (optional)
        self._redis: Optional[RedisCache] = None
        if self.config.redis_url and self.config.tier in [CacheTier.REDIS, CacheTier.HYBRID]:
            self._redis = RedisCache(
                redis_url=self.config.redis_url,
                default_ttl=self.config.redis_default_ttl,
                prefix=self.config.redis_prefix,
            )
    
    async def get(self, key: str, tier: Optional[CacheTier] = None) -> Optional[Any]:
        """
        Get a value from cache.
        
        In HYBRID mode, checks memory first, then Redis.
        """
        tier = tier or self.config.tier
        
        # Check memory first
        if tier in [CacheTier.MEMORY, CacheTier.HYBRID]:
            result = await self._memory.get(key)
            if result is not None:
                return result
        
        # Check Redis
        if tier in [CacheTier.REDIS, CacheTier.HYBRID] and self._redis:
            result = await self._redis.get(key)
            if result is not None:
                # Populate memory cache in hybrid mode
                if tier == CacheTier.HYBRID:
                    await self._memory.set(key, result)
                return result
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tier: Optional[CacheTier] = None,
    ) -> None:
        """
        Set a value in cache.
        
        In HYBRID mode, sets in both memory and Redis.
        """
        tier = tier or self.config.tier
        
        # Set in memory
        if tier in [CacheTier.MEMORY, CacheTier.HYBRID]:
            await self._memory.set(key, value, ttl)
        
        # Set in Redis
        if tier in [CacheTier.REDIS, CacheTier.HYBRID] and self._redis:
            await self._redis.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete a key from all tiers."""
        memory_deleted = await self._memory.delete(key)
        redis_deleted = False
        if self._redis:
            redis_deleted = await self._redis.delete(key)
        return memory_deleted or redis_deleted
    
    async def clear(self, prefix: str = "") -> int:
        """Clear all entries (optionally matching prefix)."""
        count = await self._memory.clear()
        if self._redis:
            count += await self._redis.clear(f"{prefix}*" if prefix else "*")
        return count
    
    async def cleanup(self) -> int:
        """Cleanup expired entries from memory cache."""
        return await self._memory.cleanup_expired()
    
    async def close(self):
        """Close all cache connections."""
        if self._redis:
            await self._redis.close()
    
    def stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        stats = {
            "tier": self.config.tier.value,
            "memory": self._memory.stats(),
        }
        if self._redis:
            stats["redis"] = self._redis.stats()
        return stats
    
    # =========================================================================
    # Decorator for Easy Caching
    # =========================================================================
    
    def cached(
        self,
        ttl: Optional[float] = None,
        prefix: str = "",
        key_builder: Optional[Callable[..., str]] = None,
    ):
        """
        Decorator for caching function results.
        
        Usage:
            @cache.cached(ttl=300, prefix="rag")
            async def get_rag_results(query: str):
                return await expensive_operation(query)
        
        Args:
            ttl: Cache TTL in seconds
            prefix: Key prefix for namespacing
            key_builder: Custom function to build cache key from args
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = _build_cache_key(func.__name__, args, kwargs)
                
                if prefix:
                    cache_key = f"{prefix}:{cache_key}"
                
                # Check cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator


# =============================================================================
# Helper Functions
# =============================================================================

def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Build a cache key from function name and arguments."""
    # Create a hashable representation
    key_data = {
        "func": func_name,
        "args": [_serialize_arg(arg) for arg in args],
        "kwargs": {k: _serialize_arg(v) for k, v in sorted(kwargs.items())},
    }
    key_json = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_json.encode()).hexdigest()


def _serialize_arg(arg: Any) -> Any:
    """Serialize an argument for cache key generation."""
    if isinstance(arg, (str, int, float, bool, type(None))):
        return arg
    elif isinstance(arg, (list, tuple)):
        return [_serialize_arg(item) for item in arg]
    elif isinstance(arg, dict):
        return {k: _serialize_arg(v) for k, v in sorted(arg.items())}
    else:
        # For objects, use string representation
        return str(arg)


def cache_key(*parts: Any) -> str:
    """Build a cache key from parts."""
    serialized = ":".join(str(part) for part in parts)
    return hashlib.md5(serialized.encode()).hexdigest()


# =============================================================================
# Predefined Cache Keys/TTLs
# =============================================================================

class CacheKeys:
    """Predefined cache key prefixes."""
    RAG = "rag"
    MODEL_STATUS = "model_status"
    PROJECT_CONTEXT = "project_ctx"
    ATTACHMENT = "attachment"
    PROVIDER_STATUS = "provider"


class CacheTTL:
    """Predefined TTL values in seconds."""
    VERY_SHORT = 30      # 30 seconds (model availability)
    SHORT = 60           # 1 minute (project context)
    MEDIUM = 300         # 5 minutes (RAG results)
    LONG = 600           # 10 minutes (attachment content)
    VERY_LONG = 3600     # 1 hour (stable data)


# =============================================================================
# Singleton
# =============================================================================

_cache: Optional[UnifiedCache] = None


def get_cache() -> UnifiedCache:
    """Get the singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = UnifiedCache()
    return _cache


async def close_cache():
    """Close the cache and cleanup resources."""
    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    cache = get_cache()
    return cache.stats()

