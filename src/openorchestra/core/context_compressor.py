"""
Intelligent context compression for memory efficiency.

Compresses conversation context while preserving technical patterns
and solutions without exponential storage growth.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List

from .pattern_signature import PatternSignature


@dataclass
class CompressedContext:
    """Compressed context containing only essential pattern information."""

    technical_patterns: List[Dict[str, object]] = field(default_factory=list)
    verified_solutions: List[str] = field(default_factory=list)
    critical_metrics: Dict[str, str] = field(default_factory=dict)
    domain_tags: List[str] = field(default_factory=list)

    def to_storage_dict(self) -> Dict[str, object]:
        """Convert to a small dictionary suitable for storage."""
        return {
            "patterns": len(self.technical_patterns),
            "solutions": len(self.verified_solutions),
            "metrics": str(self.critical_metrics)[:200],
            "tags": ",".join(self.domain_tags),
        }


class ContextCompressor:
    """Extract patterns and solutions while discarding conversational fluff."""

    ERROR_PATTERNS = [
        r"error[:\s]*",
        r"exception[:\s]*",
        r"fail[:\s]*",
        r"issue[:\s]*",
        r"bug[:\s]*",
    ]
    SOLUTION_PATTERNS = [
        r"fix[:\s]*",
        r"solution[:\s]*",
        r"recommendation[:\s]*",
        r"approach[:\s]*",
    ]
    METRIC_PATTERN = re.compile(
        r"(?P<name>accuracy|coverage|performance|score)\s*[:=]?\s*(?P<value>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    def compress_context(self, conversation: str, domain: str = "") -> CompressedContext:
        """Compress a conversation into essential patterns."""
        return CompressedContext(
            technical_patterns=self._extract_patterns(conversation, domain),
            verified_solutions=self._extract_solutions(conversation),
            critical_metrics=self._extract_metrics(conversation),
            domain_tags=[domain] if domain else [],
        )

    def _extract_patterns(self, text: str, domain: str = "") -> List[Dict[str, object]]:
        patterns: List[Dict[str, object]] = []

        for pattern in self.ERROR_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 200)
                context = text[start:end].strip()
                signature = PatternSignature.from_context(domain, "error", context)

                patterns.append(
                    {
                        "type": "error",
                        "signature": signature.__dict__,
                        "context": context[:100],
                        "source_line": match.start(),
                    }
                )

        return patterns[:10]

    def _extract_solutions(self, text: str) -> List[str]:
        solutions: List[str] = []

        for pattern in self.SOLUTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.end()
                end = min(len(text), start + 150)
                solution = text[start:end].strip()
                if solution:
                    first_line = solution.split("\n")[0].strip()
                    if first_line and first_line not in solutions:
                        solutions.append(first_line)

        return solutions[:5]

    def _extract_metrics(self, text: str) -> Dict[str, str]:
        return {
            match.group("name").lower(): match.group("value")
            for match in self.METRIC_PATTERN.finditer(text)
        }


def compress_conversation(conversation: str, domain: str = "") -> CompressedContext:
    """Convenience function for compressing a conversation."""
    return ContextCompressor().compress_context(conversation, domain)
