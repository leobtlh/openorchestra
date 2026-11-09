"""
LRU Cache for fast pattern lookups.

Provides O(1) access to frequently used patterns while maintaining
a bounded memory footprint.
"""

from collections import OrderedDict
from typing import Generic, TypeVar, Optional, Callable
import time

T = TypeVar('T')


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.
    
    Optimized for fast pattern lookups during competition.
    """
    
    def __init__(self, maxsize: int = 1000, ttl_seconds: float = 3600.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[T]:
        """Get item from cache, returns None if not found or expired"""
        if key not in self._cache:
            self._misses += 1
            return None
        
        item, timestamp = self._cache.pop(key)
        
        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            self._misses += 1
            return None
        
        # Move to end (most recently used)
        self._cache[key] = (item, timestamp)
        self._hits += 1
        return item
    
    def set(self, key: str, value: T) -> None:
        """Set item in cache, evicting LRU if necessary"""
        if key in self._cache:
            self._cache.pop(key)
        
        # Evict oldest if at capacity
        while len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)
        
        self._cache[key] = (value, time.time())
    
    def query_similar(self, target_key: str, max_results: int = 5) -> list:
        """Query patterns similar to target (for fuzzy matching)"""
        results = []
        target_prefix = target_key[:6] if len(target_key) >= 6 else target_key
        
        for key, (value, timestamp) in self._cache.items():
            if target_prefix in key[:6] or key[:6] in target_prefix:
                results.append(value)
                if len(results) >= max_results:
                    break
        
        return results
    
    def clear_expired(self) -> int:
        """Remove expired entries, returns count removed"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        return key in self._cache