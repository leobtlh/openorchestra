"""
Dynamic agent count optimizer for OpenOrchestra.

Based on research by Hovsky et al. (2023) "Evaluating the Trade-offs of
Multi-Agent Competition in Large Language Model Workflows".
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _integer_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class CompetitionMetrics:
    """Runtime metrics for competition optimization."""

    iteration: int = 0
    agent_count: int = 1
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    best_score: float = 0.0
    score_improvement: float = 0.0
    iteration_time_seconds: float = 0.0
    convergence_threshold: float = 0.03
    budget_limit_tokens: int = 50000
    budget_limit_usd: float = 50.0

    def improvement_rate(self) -> float:
        """Improvement relative to the best score."""
        if self.iteration == 0 or self.best_score <= 0:
            return 0.0
        return max(0.0, self.score_improvement / self.best_score)


class AgentOptimizer:
    """
    Dynamically determine the optimal number of agents based on:

    - Task complexity
    - Cost/quality trade-offs
    - Convergence detection

    Reference: Hovsky et al. (2023) "Evaluating the Trade-offs of
    Multi-Agent Competition in LLM Workflows".
    """

    SATURATION_FACTOR = 0.7
    MAX_AGENTS_HARD_LIMIT = 5
    DEFAULT_MAX_AGENTS = 4
    MIN_IMPROVEMENT_THRESHOLD = 0.03

    BASE_COST_PER_AGENT_TOKENS = 8000
    BASE_COST_PER_AGENT_USD = 3.0
    TOURNAMENT_OVERHEAD_FACTOR = 1.5

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.history: List[CompetitionMetrics] = []
        requested_max = _integer_value(
            self.config.get("max_agents", self.DEFAULT_MAX_AGENTS), self.DEFAULT_MAX_AGENTS
        )
        self.max_agents = min(max(1, requested_max), self.MAX_AGENTS_HARD_LIMIT)
        requested_threshold = _float_value(
            self.config.get("min_improvement_threshold", self.MIN_IMPROVEMENT_THRESHOLD),
            self.MIN_IMPROVEMENT_THRESHOLD,
        )
        self.min_improvement_threshold = min(max(0.0, requested_threshold), 1.0)
        self._cost_params = self._load_cost_params()

    def _load_cost_params(self) -> Dict[str, float]:
        return {
            "tokens_per_agent": _float_value(
                self.config.get("tokens_per_agent"), self.BASE_COST_PER_AGENT_TOKENS
            ),
            "usd_per_agent": _float_value(
                self.config.get("usd_per_agent"), self.BASE_COST_PER_AGENT_USD
            ),
            "overhead_factor": _float_value(
                self.config.get("overhead_factor"), self.TOURNAMENT_OVERHEAD_FACTOR
            ),
        }

    def _calculate_max_by_budget(self, budget_amount: float, unit_of_measure: str) -> int:
        """Calculate the maximum number of agents affordable within a budget."""
        cost_per_agent = self._cost_params[f"{unit_of_measure}_per_agent"]
        overhead = self._cost_params["overhead_factor"]
        unit_cost = cost_per_agent * overhead

        if unit_cost <= 0:
            return self.MAX_AGENTS_HARD_LIMIT

        return max(0, int(budget_amount / unit_cost))

    def calculate_optimal_agent_count(
        self,
        task_complexity: float = 0.5,
        budget_tokens: Optional[int] = None,
        budget_usd: Optional[float] = None,
        previous_improvements: Optional[List[float]] = None,
    ) -> int:
        """
        Calculate the optimal agent count.

        Uses Hovsky et al.'s model: Performance Gain = 100 / (1 + e^(-k*(n-1))).
        """
        if task_complexity < 0.3:
            base_agents = 2
        elif task_complexity < 0.7:
            base_agents = 3
        else:
            base_agents = 4

        if budget_tokens is not None:
            base_agents = min(base_agents, self._calculate_max_by_budget(budget_tokens, "tokens"))
        if budget_usd is not None:
            base_agents = min(base_agents, self._calculate_max_by_budget(budget_usd, "usd"))

        if previous_improvements and len(previous_improvements) >= 3:
            recent_gain = sum(previous_improvements[-3:]) / 3
            if recent_gain < self.min_improvement_threshold:
                base_agents = max(1, base_agents - 1)

        return min(max(base_agents, 1), self.max_agents)

    def should_reduce_agents(self, metrics: CompetitionMetrics) -> bool:
        """Return True when diminishing returns or the budget call for fewer agents."""
        if metrics.total_cost_usd > metrics.budget_limit_usd:
            return True

        if len(self.history) < 3:
            return False

        recent_scores = [item.best_score for item in self.history[-3:]]
        return max(recent_scores) - min(recent_scores) < self.min_improvement_threshold

    def estimate_performance_gain(self, agent_count: int) -> float:
        """Estimate the performance gain using the saturation curve."""
        if agent_count < 1:
            return 0.0

        gain = 100 / (1 + math.exp(-self.SATURATION_FACTOR * (agent_count - 1)))
        return min(gain / 100, 1.0)

    def get_recommendation(self) -> Dict[str, Any]:
        """Get the current optimization recommendation."""
        if not self.history:
            count = min(3, self.max_agents)
            return {
                "agent_count": count,
                "reason": "Initial recommendation",
                "expected_gain": self.estimate_performance_gain(count),
            }

        latest = self.history[-1]

        if self.should_reduce_agents(latest):
            new_count = max(1, latest.agent_count - 1)
            return {
                "agent_count": new_count,
                "reason": "Convergence detected - diminishing returns",
                "expected_gain": self.estimate_performance_gain(new_count),
            }

        current_gain = self.estimate_performance_gain(latest.agent_count)
        next_gain = self.estimate_performance_gain(latest.agent_count + 1)
        marginal_gain = next_gain - current_gain

        if marginal_gain < self.min_improvement_threshold or latest.agent_count >= self.max_agents:
            return {
                "agent_count": min(latest.agent_count, self.max_agents),
                "reason": "Marginal gain below threshold",
                "expected_gain": current_gain,
            }

        return {
            "agent_count": min(latest.agent_count + 1, self.max_agents),
            "reason": "Marginal gain exceeds threshold",
            "expected_gain": next_gain,
        }
