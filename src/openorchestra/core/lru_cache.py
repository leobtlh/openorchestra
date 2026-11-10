"""
LRU Cache for fast pattern lookups.

Provides O(1) access to frequently used patterns while maintaining
a bounded memory footprint.
"""

import threading
import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with per-entry TTL support.

    Optimized for fast pattern lookups during a competition.
    """

    def __init__(self, maxsize: int = 1000, ttl_seconds: float = 3600.0):
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must not be negative")

        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: "OrderedDict[str, tuple[T, float, float]]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache, or None if missing/expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            value, timestamp, ttl = entry
            if time.time() - timestamp > ttl:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to the end (most recently used).
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: T, ttl_seconds: Optional[float] = None) -> None:
        """Set an item, evicting the least recently used entry if necessary."""
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl < 0:
            raise ValueError("ttl_seconds must not be negative")

        with self._lock:
            self._cache.pop(key, None)
            while len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = (value, time.time(), ttl)

    def query_similar(self, target_key: str, max_results: int = 5) -> list[T]:
        """Return cached values whose key shares the target's six-character prefix."""
        target_prefix = target_key[:6]
        results: list[T] = []

        with self._lock:
            now = time.time()
            for key, (value, timestamp, ttl) in self._cache.items():
                if now - timestamp > ttl:
                    continue
                if key[:6] == target_prefix:
                    results.append(value)
                    if len(results) >= max_results:
                        break

        return results

    def clear_expired(self) -> int:
        """Remove expired entries and return the number removed."""
        now = time.time()
        with self._lock:
            expired = [
                key for key, (_, timestamp, ttl) in self._cache.items() if now - timestamp > ttl
            ]
            for key in expired:
                del self._cache[key]
        return len(expired)

    def clear(self) -> None:
        """Remove every entry from the cache."""
        with self._lock:
            self._cache.clear()

    def delete(self, key: str) -> bool:
        """Remove one entry; return True when it existed."""
        with self._lock:
            return self._cache.pop(key, None) is not None

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total else 0.0

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            _, timestamp, ttl = entry
            return time.time() - timestamp <= ttl
