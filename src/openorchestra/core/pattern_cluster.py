"""
Semantic clustering of patterns for efficient storage and retrieval.

Groups similar patterns together to reduce storage needs and
improve pattern discovery.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .pattern_signature import PatternSignature


@dataclass
class PatternCluster:
    """Cluster of semantically similar patterns."""

    centroid: PatternSignature
    members: List[Dict[str, Any]] = field(default_factory=list)
    cluster_frequency: int = 0
    best_solutions: List[str] = field(default_factory=list)
    domain: str = ""

    def add_member(
        self,
        pattern_data: Dict[str, Any],
        solution: str = "",
        score: float = 0.0,
    ) -> bool:
        """Add a pattern if it is similar enough to the centroid."""
        member_sig = PatternSignature(**pattern_data.get("signature", {}))

        if not self._is_similar(member_sig):
            return False

        self.members.append(
            {
                "signature": member_sig.__dict__,
                "solution": solution,
                "score": score,
                "timestamp": pattern_data.get("timestamp", ""),
            }
        )
        self.cluster_frequency += 1

        if solution and solution not in self.best_solutions:
            self.best_solutions.append(solution)
            self.best_solutions = self.best_solutions[-3:]

        return True

    def _is_similar(self, other: PatternSignature, threshold: float = 0.7) -> bool:
        """Check whether a pattern belongs to this cluster."""
        return self.centroid.similarity_score(other) >= threshold

    def to_compact_dict(self) -> Dict[str, Any]:
        """Convert to a compact dictionary for storage."""
        return {
            "centroid": self.centroid.__dict__,
            "frequency": self.cluster_frequency,
            "best_solutions": self.best_solutions[:3],
            "domain": self.domain,
            "member_count": len(self.members),
        }

    @classmethod
    def from_compact_dict(cls, data: Dict[str, Any]) -> "PatternCluster":
        """Create a cluster from a compact dictionary."""
        return cls(
            centroid=PatternSignature(**data["centroid"]),
            members=[],
            cluster_frequency=data.get("frequency", 0),
            best_solutions=data.get("best_solutions", []),
            domain=data.get("domain", ""),
        )


class PatternClusterManager:
    """Manage clusters of patterns for efficient storage."""

    def __init__(self, max_clusters: int = 100):
        if max_clusters < 1:
            raise ValueError("max_clusters must be at least 1")
        self.max_clusters = max_clusters
        self.clusters: Dict[str, PatternCluster] = {}

    def add_pattern(self, pattern_data: Dict[str, Any], solution: str = "") -> str:
        """Add a pattern to the matching cluster, creating it if needed."""
        sig_data = pattern_data.get("signature", {})
        if not sig_data:
            return "new_cluster"

        signature = PatternSignature(**sig_data)
        cluster_id = f"{signature.domain_signature}:{signature.category_signature}"

        cluster = self.clusters.get(cluster_id)
        if cluster is None:
            cluster = PatternCluster(centroid=signature, domain=signature.domain_signature)
            self.clusters[cluster_id] = cluster
            self._evict_if_needed()

        cluster.add_member(pattern_data, solution, pattern_data.get("score", 0))
        return cluster_id

    def _evict_if_needed(self) -> None:
        while len(self.clusters) > self.max_clusters:
            oldest_key = next(iter(self.clusters))
            del self.clusters[oldest_key]

    def get_clusters_for_domain(self, domain: str) -> List[PatternCluster]:
        """Get all clusters for a specific domain."""
        return [cluster for cluster in self.clusters.values() if cluster.domain == domain]

    def get_all_clusters(self) -> List[PatternCluster]:
        """Get all clusters."""
        return list(self.clusters.values())
