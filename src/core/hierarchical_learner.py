"""
Hierarchical learning system for pattern optimization.

Implements multi-level learning from domain to global patterns
with feedback propagation.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from .pattern_signature import PatternSignature
from .pattern_cluster import PatternClusterManager


@dataclass
class Lesson:
    """Represents a learned lesson from a competition"""
    pattern_type: str
    domain: str
    signature: str
    confidence: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    related_domains: List[str] = field(default_factory=list)
    timestamp: str = ""


class HierarchicalLearner:
    """
    Learns patterns hierarchically from competition results.
    
    Propagation levels:
    1. Sub-domain patterns (specific)
    2. Domain patterns (general)
    3. Global patterns (universal)
    """
    
    def __init__(self):
        self.domain_knowledge: Dict[str, Dict] = {}
        self.subdomain_knowledge: Dict[str, Dict] = {}
        self.global_patterns: Set[str] = set()
        self.pattern_history: List[str] = []  # For TTL management
    
    def learn_from_competition(
        self,
        domain: str,
        agent_id: str,
        pattern_type: str,
        solution: str,
        score: float,
        is_winning: bool = False
    ) -> str:
        """
        Learn from a competition result.
        Returns the pattern signature for storage.
        """
        # Create pattern signature
        sig = PatternSignature.from_context(domain, pattern_type, solution)
        
        # Store at appropriate level
        if is_winning:
            self._store_winning_pattern(sig, domain, score, solution)
        else:
            self._store_learning_pattern(sig, domain, score, solution)
        
        # Update global patterns periodically
        if len(self.pattern_history) % 10 == 0:
            self._propagate_to_global(sig, domain)
        
        # Maintain history size
        self.pattern_history.append(sig.pattern_fingerprint)
        if len(self.pattern_history) > 1000:
            self.pattern_history = self.pattern_history[-500:]
        
        return sig.to_compact_vector()
    
    def _store_winning_pattern(
        self,
        signature: PatternSignature,
        domain: str,
        score: float,
        solution: str
    ) -> None:
        """Store a winning pattern at domain level"""
        if domain not in self.domain_knowledge:
            self.domain_knowledge[domain] = {
                'patterns': {},
                'solutions': [],
                'performance_metrics': []
            }
        
        domain_k = self.domain_knowledge[domain]
        sig_key = signature.to_compact_vector()
        
        if sig_key in domain_k['patterns']:
            # Update existing
            domain_k['patterns'][sig_key]['confidence'] = min(1.0, 
                domain_k['patterns'][sig_key]['confidence'] + 0.1)
            domain_k['patterns'][sig_key]['score_history'].append(score)
        else:
            # Add new
            domain_k['patterns'][sig_key] = {
                'signature': signature,
                'confidence': 0.8,
                'solution': solution,
                'score_history': [score],
                'last_updated': datetime.now().isoformat()
            }
        
        domain_k['solutions'].append(solution)
        domain_k['performance_metrics'].append(score)
    
    def _store_learning_pattern(
        self,
        signature: PatternSignature,
        domain: str,
        score: float,
        solution: str
    ) -> None:
        """Store a pattern for general learning"""
        sig_key = signature.to_compact_vector()
        
        # Add to domain knowledge if exists
        if domain in self.domain_knowledge:
            self.domain_knowledge[domain]['patterns'][sig_key] = {
                'signature': signature,
                'confidence': 0.5,
                'solution': solution,
                'score': score
            }
        
        # Track as potential global pattern
        self.global_patterns.add(sig_key)
    
    def _propagate_to_global(self, signature: PatternSignature, domain: str) -> None:
        """Propagate patterns to global level after sufficient examples"""
        sig_key = signature.to_compact_vector()
        
        # Only propagate patterns seen > 3 times
        pattern_usage = sum(
            1 for k, v in self.domain_knowledge.get(domain, {}).get('patterns', {}).items()
            if signature.pattern_fingerprint[:6] in k
        )
        
        if pattern_usage >= 3:
            self.global_patterns.add(sig_key)
    
    def get_relevant_patterns(self, query_signature: PatternSignature, max_results: int = 5) -> List[Dict]:
        """Get patterns relevant to a query"""
        results = []
        query_domain = query_signature.domain_signature
        
        # Priority 1: Domain-specific patterns
        if query_domain in self.domain_knowledge:
            results.extend(self._get_similar_patterns(
                query_signature,
                self.domain_knowledge[query_domain]['patterns'],
                max_results
            ))
        
        # Priority 2: Global patterns
        if len(results) < max_results:
            results.extend(self._get_global_patterns(query_signature, max_results - len(results)))
        
        return results[:max_results]
    
    def _get_similar_patterns(self, query_sig: PatternSignature, pattern_dict: Dict, max_results: int) -> List[Dict]:
        """Get patterns similar to query within a domain"""
        similar = []
        
        for sig_key, pattern_data in pattern_dict.items():
            if 'signature' in pattern_data:
                sim = query_sig.similarity_score(pattern_data['signature'])
                if sim > 0.5:
                    similar.append({
                        'pattern': pattern_data,
                        'similarity': sim
                    })
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)[:max_results]
    
    def _get_global_patterns(self, query_sig: PatternSignature, max_results: int) -> List[Dict]:
        """Get globally relevant patterns"""
        # Global patterns are simplified - just return top candidates
        return [{'pattern': {'global': True, 'similarity': 0.7}, 'similarity': 0.7}]


def propagate_domain_pattern(global_patterns: Set[str], domain_patterns: List[str]) -> List[str]:
    """Utility function to propagate patterns from domain to global"""
    return list(set(global_patterns) | set(domain_patterns))