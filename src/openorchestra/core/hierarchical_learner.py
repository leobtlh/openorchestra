"""
Hierarchical learning system for pattern optimization.

Implements multi-level learning from domain to global patterns
with feedback propagation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Set

from .pattern_signature import PatternSignature

MAX_HISTORY = 1000
TRIM_TO = 500


@dataclass
class Lesson:
    """Represents a learned lesson from a competition."""

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
    Learn patterns hierarchically from competition results.

    Propagation levels:
    1. Sub-domain patterns (specific)
    2. Domain patterns (general)
    3. Global patterns (universal)
    """

    def __init__(self) -> None:
        self.domain_knowledge: Dict[str, Dict[str, Any]] = {}
        self.subdomain_knowledge: Dict[str, Dict] = {}
        self.global_patterns: Set[str] = set()
        self.pattern_history: List[str] = []

    def learn_from_competition(
        self,
        domain: str,
        agent_id: str,
        pattern_type: str,
        solution: str,
        score: float,
        is_winning: bool = False,
    ) -> str:
        """Learn from a competition result and return the pattern fingerprint."""
        signature = PatternSignature.from_context(domain, pattern_type, solution)
        key = signature.to_compact_vector()

        if is_winning:
            self._store_winning_pattern(signature, domain, score, solution)
        else:
            self._store_learning_pattern(signature, domain, score, solution)

        self.pattern_history.append(key)
        if len(self.pattern_history) > MAX_HISTORY:
            self.pattern_history = self.pattern_history[-TRIM_TO:]

        if self.pattern_history.count(key) >= 3:
            self.global_patterns.add(key)

        return key

    def _ensure_domain(self, domain: str) -> Dict[str, Any]:
        return self.domain_knowledge.setdefault(
            domain,
            {"patterns": {}, "solutions": [], "performance_metrics": []},
        )

    def _store_winning_pattern(
        self,
        signature: PatternSignature,
        domain: str,
        score: float,
        solution: str,
    ) -> None:
        """Store a winning pattern at the domain level."""
        knowledge = self._ensure_domain(domain)
        key = signature.to_compact_vector()

        existing = knowledge["patterns"].get(key)
        if existing is None:
            knowledge["patterns"][key] = {
                "signature": signature,
                "confidence": 0.8,
                "solution": solution,
                "score_history": [score],
                "last_updated": datetime.now().isoformat(),
            }
        else:
            existing["confidence"] = min(1.0, float(existing.get("confidence", 0.5)) + 0.1)
            existing.setdefault("score_history", []).append(score)
            existing["solution"] = solution
            existing["last_updated"] = datetime.now().isoformat()

        knowledge["solutions"].append(solution)
        knowledge["performance_metrics"].append(score)

    def _store_learning_pattern(
        self,
        signature: PatternSignature,
        domain: str,
        score: float,
        solution: str,
    ) -> None:
        """Store a non-winning pattern for general learning."""
        knowledge = self._ensure_domain(domain)
        key = signature.to_compact_vector()

        existing = knowledge["patterns"].get(key)
        if existing is not None:
            # Never downgrade a previously learned winning pattern.
            existing["last_updated"] = datetime.now().isoformat()
            self.global_patterns.add(key)
            return

        knowledge["patterns"][key] = {
            "signature": signature,
            "confidence": 0.5,
            "solution": solution,
            "score": score,
            "last_updated": datetime.now().isoformat(),
        }
        self.global_patterns.add(key)

    def get_relevant_patterns(
        self, query_signature: PatternSignature, max_results: int = 5
    ) -> List[Dict]:
        """Get patterns relevant to a query, domain-first then global."""
        results: List[Dict] = []
        query_domain = query_signature.domain_signature

        domain_patterns = self.domain_knowledge.get(query_domain, {}).get("patterns", {})
        results.extend(self._get_similar_patterns(query_signature, domain_patterns, max_results))

        if len(results) < max_results:
            results.extend(self._get_global_patterns(query_signature, max_results - len(results)))

        return results[:max_results]

    def _get_similar_patterns(
        self,
        query_sig: PatternSignature,
        pattern_dict: Dict[str, Dict[str, Any]],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Get patterns similar to a query within a domain."""
        similar: List[Dict[str, Any]] = []
        for pattern_data in pattern_dict.values():
            candidate = pattern_data.get("signature")
            if candidate is None:
                continue
            similarity = query_sig.similarity_score(candidate)
            if similarity > 0.5:
                similar.append({"pattern": pattern_data, "similarity": similarity})

        return sorted(similar, key=lambda item: item["similarity"], reverse=True)[:max_results]

    def _get_global_patterns(self, query_sig: PatternSignature, max_results: int) -> List[Dict]:
        """Get globally relevant patterns from every known domain."""
        candidates: List[Dict[str, Any]] = []
        seen: Set[int] = set()

        for knowledge in self.domain_knowledge.values():
            for key, pattern in knowledge["patterns"].items():
                if key not in self.global_patterns or id(pattern) in seen:
                    continue
                seen.add(id(pattern))
                similarity = query_sig.similarity_score(pattern["signature"])
                if similarity > 0.5:
                    candidates.append({"pattern": pattern, "similarity": similarity})

        return sorted(candidates, key=lambda item: item["similarity"], reverse=True)[:max_results]


def propagate_domain_pattern(global_patterns: Set[str], domain_patterns: List[str]) -> List[str]:
    """Utility function to propagate patterns from domain to global."""
    return list(set(global_patterns) | set(domain_patterns))
