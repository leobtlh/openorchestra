"""Tests for pattern signatures and clustering."""

from openorchestra.core.pattern_cluster import PatternCluster, PatternClusterManager
from openorchestra.core.pattern_signature import PatternSignature


def test_signature_is_stable_and_compact() -> None:
    first = PatternSignature.from_context("backend", "security", "SELECT 1")
    second = PatternSignature.from_context("backend", "security", "SELECT 1")
    other = PatternSignature.from_context("backend", "security", "SELECT 2")

    assert first.pattern_fingerprint == second.pattern_fingerprint
    assert first.pattern_fingerprint != other.pattern_fingerprint
    assert len(first.pattern_fingerprint) == 12
    assert first.to_compact_vector() == first.pattern_fingerprint
    assert first.domain_signature == "backend"


def test_similarity_prefers_same_domain_and_category() -> None:
    base = PatternSignature.from_context("backend", "security", "abc")
    same = PatternSignature.from_context("backend", "security", "xyz")
    other = PatternSignature.from_context("frontend", "design", "xyz")

    assert base.similarity_score(same) > base.similarity_score(other)
    assert base.similarity_score(same) >= 0.7


def test_empty_hash_similarity_is_zero() -> None:
    assert PatternSignature._approximate_hash_similarity("", "abc") == 0.0


def _pattern(signature: PatternSignature, solution: str = "s") -> dict:
    return {"signature": signature.__dict__, "score": 1.0}


def test_clusters_group_same_domain_and_category() -> None:
    manager = PatternClusterManager(max_clusters=10)
    a = PatternSignature.from_context("backend", "security", "a")
    b = PatternSignature.from_context("backend", "security", "b")

    first = manager.add_pattern(_pattern(a), "solution a")
    second = manager.add_pattern(_pattern(b), "solution b")

    assert first == second
    assert len(manager.clusters) == 1
    assert manager.clusters[first].cluster_frequency == 2


def test_different_domains_get_different_clusters() -> None:
    manager = PatternClusterManager(max_clusters=10)
    backend = PatternSignature.from_context("backend", "security", "a")
    frontend = PatternSignature.from_context("frontend", "security", "a")

    assert manager.add_pattern(_pattern(backend)) != manager.add_pattern(_pattern(frontend))


def test_cluster_capacity_is_bounded() -> None:
    manager = PatternClusterManager(max_clusters=2)
    for index in range(5):
        signature = PatternSignature.from_context(f"domain{index}", "security", "a")
        manager.add_pattern(_pattern(signature))

    assert len(manager.clusters) == 2


def test_best_solutions_are_capped() -> None:
    signature = PatternSignature.from_context("backend", "security", "a")
    cluster = PatternCluster(centroid=signature, domain="backend")

    for index in range(5):
        cluster.add_member(_pattern(signature), f"solution {index}")

    assert len(cluster.best_solutions) == 3


def test_compact_roundtrip() -> None:
    signature = PatternSignature.from_context("backend", "security", "a")
    cluster = PatternCluster(centroid=signature, domain="backend")
    cluster.add_member(_pattern(signature), "solution")

    restored = PatternCluster.from_compact_dict(cluster.to_compact_dict())

    assert restored.centroid == cluster.centroid
    assert restored.cluster_frequency == cluster.cluster_frequency
    assert restored.best_solutions == cluster.best_solutions
    assert restored.members == []


def test_empty_signature_returns_default_cluster_id() -> None:
    assert PatternClusterManager().add_pattern({}) == "new_cluster"
