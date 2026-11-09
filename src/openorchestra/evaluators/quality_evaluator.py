"""
Quality evaluator for OpenOrchestra.

Evaluates agent outputs against domain-specific criteria using deterministic
static heuristics (complexity, tests, security signals, documentation, ...).
"""

import logging
import re
from typing import Any, Dict, Iterable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Keyword signals used to score a solution for a given criterion family.
CRITERION_SIGNALS: Dict[str, tuple[str, ...]] = {
    "code_quality": (
        "def ",
        "class ",
        "import ",
        "return",
        "try:",
        "except",
        "logging",
        "test_",
        "assert",
    ),
    "quality": (
        "def ",
        "class ",
        "import ",
        "return",
        "try:",
        "except",
        "logging",
        "test_",
        "assert",
    ),
    "test": ("test_", "assert", "pytest", "unittest", "fixture", "mock", "coverage"),
    "security": (
        "valid",
        "raise",
        "try:",
        "except",
        "parameter",
        "query",
        "auth",
        "encrypt",
        "sanitize",
        "logging",
    ),
    "vulnerab": (
        "valid",
        "raise",
        "parameter",
        "escape",
        "sanitize",
        "auth",
        "encrypt",
        "permission",
    ),
    "complian": ("valid", "auth", "encrypt", "audit", "logging", "policy", "permission"),
    "threat": ("valid", "auth", "encrypt", "permission", "raise", "logging", "sanitize"),
    "access": (
        "aria",
        "alt=",
        "role=",
        "label",
        "keyboard",
        "contrast",
        "screen reader",
        "tabindex",
    ),
    "responsive": ("@media", "flex", "grid", "viewport", "rem", "clamp(", "breakpoint"),
    "design": ("token", "component", "layout", "theme", "color", "spacing", "typography"),
    "performance": ("cache", "async", "await", "index", "pool", "batch", "lazy", "complexity"),
    "optimization": ("cache", "async", "await", "index", "pool", "batch", "lazy", "complexity"),
    "efficien": ("cache", "async", "await", "index", "pool", "batch", "lazy", "complexity"),
    "scalab": ("async", "pool", "batch", "queue", "cache", "shard", "replica", "index"),
    "maintain": ("def ", "class ", '"""', "typing", "type", "docstring", "logging", "test_"),
    "consisten": ("def ", "class ", '"""', "typing", "logging", "test_"),
    "database": ("query", "index", "transaction", "parameter", "schema", "migration", "pool"),
    "api": ("endpoint", "request", "response", "status", "async", "await", "valid", "raise"),
    "pipeline": ("async", "await", "batch", "queue", "retry", "transaction", "valid"),
    "data": ("valid", "schema", "type", "query", "test_", "assert"),
    "model": ("def ", "class ", "import ", "train", "predict", "valid", "assert"),
    "infra": ("docker", "kubernetes", "config", "deploy", "logging", "monitor", "health"),
    "deploy": ("docker", "kubernetes", "config", "deploy", "health", "rollback"),
    "monitor": ("logging", "metric", "health", "alert", "trace", "log"),
    "cost": ("cache", "batch", "lazy", "pool", "index", "efficient"),
    "reliab": ("try:", "except", "retry", "timeout", "raise", "valid", "health"),
    "fault": ("try:", "except", "retry", "timeout", "raise", "fallback"),
    "architect": ("def ", "class ", "import ", "typing", "interface", "pattern", "modular"),
    "competition": ("agent", "score", "evaluat", "select", "tournament", "def "),
    "agent": ("agent", "score", "evaluat", "select", "def ", "async"),
    "learning": ("agent", "score", "learn", "pattern", "evaluat"),
    "bug": ("test_", "assert", "raise", "try:", "except", "fix"),
    "automation": ("test_", "assert", "pytest", "script", "async", "def "),
    "technology": ("import ", "class ", "interface", "pattern", "typing"),
}

GENERAL_SIGNALS = ("def ", "class ", "import ", "return", "try:", "except", "test_", "assert")


class EvaluationResult(BaseModel):
    """Result of an evaluation."""

    agent_id: str
    total_score: float
    criteria_scores: Dict[str, float]
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)


def _clean_weights(raw: Iterable[tuple[Any, Any]]) -> Dict[str, float]:
    """Keep only valid, strictly positive criterion weights."""
    weights: Dict[str, float] = {}
    for name, weight in raw:
        try:
            value = float(weight)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid criterion weight: %r=%r", name, weight)
            continue
        if value > 0:
            weights[str(name)] = value
    return weights


def _normalise_criteria(criteria: Any) -> Dict[str, float]:
    """Accept mappings and the legacy list-of-mappings format."""
    if isinstance(criteria, dict):
        return _clean_weights(criteria.items())

    if isinstance(criteria, Iterable) and not isinstance(criteria, (str, bytes)):
        entries: list[tuple[Any, Any]] = []
        for entry in criteria:
            if isinstance(entry, dict):
                entries.extend(entry.items())
        return _clean_weights(entries)

    return {}


class QualityEvaluator:
    """Evaluate agent outputs against weighted quality criteria."""

    def __init__(self, quality_threshold: float = 0.7):
        if not 0.0 <= quality_threshold <= 1.0:
            raise ValueError("quality_threshold must be between 0 and 1")
        self.quality_threshold = quality_threshold
        self.criteria_weights: Dict[str, float] = {}

    def evaluate(
        self,
        solution: str,
        agent_id: str,
        domain: str,
        criteria: Any,
    ) -> EvaluationResult:
        """Evaluate a solution against the given weighted criteria."""
        weights = _normalise_criteria(criteria)
        self.criteria_weights = weights

        if not solution.strip() or not weights:
            return EvaluationResult(
                agent_id=agent_id,
                total_score=0.0,
                criteria_scores={name: 0.0 for name in weights},
                passed=False,
                details={"domain": domain, "solution_length": len(solution)},
            )

        criteria_scores = {
            criterion: self._evaluate_criterion(criterion, solution, domain)
            for criterion in weights
        }
        total_weight = sum(weights.values())
        weighted = sum(scores * weights[name] for name, scores in criteria_scores.items())
        total_score = weighted / total_weight if total_weight > 0 else 0.0

        return EvaluationResult(
            agent_id=agent_id,
            total_score=total_score,
            criteria_scores=criteria_scores,
            passed=total_score >= self.quality_threshold,
            details={
                "domain": domain,
                "solution_length": len(solution),
                "criteria_weights": weights,
            },
        )

    def _evaluate_criterion(self, criterion: str, solution: str, domain: str) -> float:
        """Score a solution for a single criterion."""
        name = criterion.lower()
        signals = next(
            (values for key, values in CRITERION_SIGNALS.items() if key in name),
            None,
        )
        if signals is None:
            return 0.5

        text = solution.lower()
        matches = sum(1 for signal in signals if signal in text)
        score = 0.45 + min(0.35, matches * 0.05)

        if re.search(r"\b(def|class|function|import|return)\b", text):
            score += 0.08
        score += min(len(solution) / 4000, 0.12)

        return min(score, 1.0)
