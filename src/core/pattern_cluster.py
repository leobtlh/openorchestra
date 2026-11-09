"""
Semantic clustering of patterns for efficient storage and retrieval.

Groups similar patterns together to reduce storage needs and 
improve pattern discovery.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from .pattern_signature import PatternSignature


@dataclass
class PatternCluster:
    """
    Cluster of semantically similar patterns.
    
    Groups patterns by similarity to reduce storage and improve retrieval.
    """
    centroid: PatternSignature
    members: List[Dict] = field(default_factory=list)
    cluster_frequency: int = 0
    best_solutions: List[str] = field(default_factory=list)
    domain: str = ""
    
    def __post_init__(self):
        """Initialize derived properties"""
        if isinstance(self.centroid, dict):
            self.centroid = PatternSignature(**self.centroid)
    
    def add_member(self, pattern_data: Dict, solution: str = "", score: float = 0.0) -> bool:
        """
        Add a pattern to the cluster if it's similar enough.
        Returns True if added, False otherwise.
        """
        member_sig = PatternSignature(**pattern_data.get('signature', {}))
        
        if self._is_similar(member_sig):
            self.members.append({
                'signature': member_sig.__dict__,
                'solution': solution,
                'score': score,
                'timestamp': pattern_data.get('timestamp', '')
            })
            
            # Update frequency
            self.cluster_frequency += 1
            
            # Update best solutions
            if solution and solution not in self.best_solutions:
                self.best_solutions.append(solution)
                if len(self.best_solutions) > 3:  # Keep top 3
                    self.best_solutions = self.best_solutions[-3:]
            
            return True
        
        return False
    
    def _is_similar(self, other: PatternSignature, threshold: float = 0.7) -> bool:
        """Check if pattern is similar to cluster centroid"""
        return self.centroid.similarity_score(other) >= threshold
    
    def to_compact_dict(self) -> Dict:
        """Convert to compact dictionary for storage"""
        return {
            'centroid': self.centroid.__dict__,
            'frequency': self.cluster_frequency,
            'best_solutions': self.best_solutions[:3],  # Top 3 only
            'domain': self.domain,
            'member_count': len(self.members)
        }
    
    @classmethod
    def from_compact_dict(cls, data: Dict) -> "PatternCluster":
        """Create cluster from compact dictionary"""
        return cls(
            centroid=PatternSignature(**data['centroid']),
            members=[],
            cluster_frequency=data.get('frequency', 0),
            best_solutions=data.get('best_solutions', []),
            domain=data.get('domain', '')
        )


class PatternClusterManager:
    """
    Manages clusters of patterns for efficient storage.
    """
    
    def __init__(self, max_clusters: int = 100):
        self.max_clusters = max_clusters
        self.clusters: Dict[str, PatternCluster] = {}
    
    def add_pattern(self, pattern_data: Dict, solution: str = "") -> str:
        """
        Add a pattern to appropriate cluster or create new one.
        Returns cluster ID.
        """
        sig_data = pattern_data.get('signature', {})
        if not sig_data:
            return "new_cluster"
        
        signature = PatternSignature(**sig_data)
        cluster_id = signature.pattern_fingerprint[:8]
        
        if cluster_id in self.clusters:
            cluster = self.clusters[cluster_id]
            cluster.add_member(pattern_data, solution, pattern_data.get('score', 0))
        else:
            # Create new cluster
            cluster = PatternCluster(
                centroid=signature,
                domain=signature.domain_signature
            )
            cluster.add_member(pattern_data, solution, pattern_data.get('score', 0))
            self.clusters[cluster_id] = cluster
            
            # Evict oldest if over capacity
            if len(self.clusters) > self.max_clusters:
                oldest_key = next(iter(self.clusters))
                del self.clusters[oldest_key]
        
        return cluster_id
    
    def get_clusters_for_domain(self, domain: str) -> List[PatternCluster]:
        """Get all clusters for a specific domain"""
        return [
            c for c in self.clusters.values()
            if c.domain == domain
        ]
    
    def get_all_clusters(self) -> List[PatternCluster]:
        """Get all clusters"""
        return list(self.clusters.values())