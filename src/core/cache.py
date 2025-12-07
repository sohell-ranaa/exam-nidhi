"""
Y6 Practice Exam - Redis Cache Module
(Simplified from ssh-guardian v3)
"""

import redis
import json
from typing import Any, Optional
from datetime import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# Cache TTL defaults (in seconds)
CACHE_TTL = {
    'subjects': 3600,        # 1 hour
    'question_sets': 1800,   # 30 minutes
    'user_data': 600,        # 10 minutes
    'exam_data': 300,        # 5 minutes
}

# Global Redis connection
_redis_client = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client"""
    global _redis_client

    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except (redis.ConnectionError, redis.TimeoutError):
            _redis_client = None

    try:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            socket_timeout=5,
            decode_responses=True
        )
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        print(f"[Cache] Redis connection failed: {e}")
        return None


def cache_key(*args) -> str:
    """Generate a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    return f"y6exam:{':'.join(key_parts)}"


class CacheManager:
    """Cache management for Y6 Practice Exam"""

    def __init__(self):
        self.client = get_redis_client()
        self.enabled = self.client is not None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"[Cache] Get error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL"""
        if not self.enabled:
            return False

        try:
            serialized = json.dumps(value, default=self._json_serializer)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"[Cache] Set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self.enabled:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"[Cache] Delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.enabled:
            return 0

        try:
            keys = self.client.keys(f"y6exam:{pattern}*")
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"[Cache] Delete pattern error for {pattern}: {e}")
            return 0

    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__float__'):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Global cache manager instance
_cache_manager = None


def get_cache() -> CacheManager:
    """Get or create the global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(key_prefix: str, ttl: int = 300):
    """
    Decorator for caching function results

    Usage:
        @cached('user_data', ttl=600)
        def get_user(user_id):
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            if not cache.enabled:
                return func(*args, **kwargs)

            # Build cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = cache_key(*key_parts)

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl)

            return result

        # Add method to clear cache for this function
        def clear_cache(*args, **kwargs):
            cache = get_cache()
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = cache_key(*key_parts)
            cache.delete(key)

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern

    Usage:
        invalidate_cache('user_data:*')
        invalidate_cache('analytics:*')
    """
    cache = get_cache()
    return cache.delete_pattern(pattern)
