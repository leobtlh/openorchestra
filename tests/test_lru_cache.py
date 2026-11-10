"""Tests for the LRU cache."""

from openorchestra.core.lru_cache import LRUCache


def test_set_and_get() -> None:
    cache: LRUCache[dict] = LRUCache(maxsize=2)
    cache.set("a", {"value": 1})
    assert cache.get("a") == {"value": 1}
    assert "a" in cache
    assert len(cache) == 1


def test_hit_rate_and_lru_eviction_order() -> None:
    cache: LRUCache[int] = LRUCache(maxsize=2)
    assert cache.get("missing") is None
    cache.set("hit", 1)
    assert cache.get("hit") == 1
    assert cache.hit_rate == 0.5

    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # "a" is now the most recently used
    cache.set("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_per_entry_ttl_override() -> None:
    cache: LRUCache[str] = LRUCache(maxsize=2, ttl_seconds=3600)
    cache.set("short", "value", ttl_seconds=0)
    assert cache.get("short") is None


def test_clear_and_clear_expired() -> None:
    cache: LRUCache[int] = LRUCache(maxsize=5)
    cache.set("a", 1)
    cache.set("b", 2, ttl_seconds=0)
    assert cache.clear_expired() == 1
    assert "a" in cache
    cache.clear()
    assert len(cache) == 0


def test_query_similar_matches_prefix_and_skips_expired() -> None:
    cache: LRUCache[int] = LRUCache(maxsize=10)
    cache.set("abcdef_one", 1)
    cache.set("abcdef_two", 2)
    cache.set("abcdef_three", 3)
    cache.set("abcdef_expired", 4, ttl_seconds=0)
    cache.set("other_key", 5)

    assert cache.query_similar("abcdef_target", max_results=2) == [1, 2]
    assert cache.query_similar("abcdef_target", max_results=10) == [1, 2, 3]
    assert cache.query_similar("missing_target") == []


def test_delete_removes_entry() -> None:
    cache: LRUCache[int] = LRUCache(maxsize=2)
    cache.set("a", 1)

    assert cache.delete("a") is True
    assert cache.delete("a") is False
    assert "a" not in cache


def test_replacing_key_refreshes_value() -> None:
    cache: LRUCache[int] = LRUCache(maxsize=2)
    cache.set("a", 1)
    cache.set("a", 2)
    assert cache.get("a") == 2
    assert len(cache) == 1
