"""
Hierarchical pattern signatures for efficient matching and storage.

Provides multi-level signatures for faster lookup and clustering.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List


@dataclass
class PatternSignature:
    """
    Multi-level hierarchical signature for pattern identification.

    Format: domain:category:code_hash
    """

    domain: str = ""
    category: str = ""
    code_hash: str = ""

    @property
    def domain_signature(self) -> str:
        """Signature at the domain level."""
        return self.domain.replace(" ", "_").lower()

    @property
    def category_signature(self) -> str:
        """Signature at the sub-domain level."""
        return self.category.replace(" ", "_").lower()

    @property
    def pattern_fingerprint(self) -> str:
        """Compact fingerprint for fast lookup."""
        combined = f"{self.domain_signature}:{self.category_signature}:{self.code_hash}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()[:12]

    def to_compact_vector(self) -> str:
        """Compact vector representation for database storage."""
        return self.pattern_fingerprint

    @classmethod
    def from_context(cls, domain: str, category: str, code_sample: str) -> "PatternSignature":
        """Create a signature from a domain, category and code sample."""
        code_hash = hashlib.md5(code_sample.encode(), usedforsecurity=False).hexdigest()[:8]
        return cls(domain=domain, category=category, code_hash=code_hash)

    def similarity_score(self, other: "PatternSignature") -> float:
        """Calculate a similarity score between two patterns."""
        domain_match = 1.0 if self.domain_signature == other.domain_signature else 0.0
        category_match = 1.0 if self.category_signature == other.category_signature else 0.0
        hash_similarity = self._approximate_hash_similarity(self.code_hash, other.code_hash)
        return domain_match * 0.4 + category_match * 0.3 + hash_similarity * 0.3

    @staticmethod
    def _approximate_hash_similarity(hash1: str, hash2: str) -> float:
        """Approximate similarity between two hash strings."""
        if not hash1 or not hash2:
            return 0.0
        matches = sum(c1 == c2 for c1, c2 in zip(hash1, hash2))
        return matches / max(len(hash1), len(hash2))


@dataclass
class PatternMetadata:
    """Metadata for a learned pattern."""

    pattern_type: str
    frequency: int = 1
    success_count: int = 0
    failure_count: int = 0
    avg_score: float = 0.0
    last_seen: str = ""
    related_patterns: List[str] = field(default_factory=list)
