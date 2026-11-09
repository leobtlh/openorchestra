"""
Dynamic agent count optimizer for OpenOrchestra.

Based on research by Hovsky et al. (2023) "Evaluating the Trade-offs of 
Multi-Agent Competition in Large Language Model Workflows".
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel


@dataclass
class CompetitionMetrics:
    """Runtime metrics for competition optimization"""
    iteration: int = 0
    agent_count: int = 1
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    best_score: float = 0.0
    score_improvement: float = 0.0
    iteration_time_seconds: float = 0.0
    convergence_threshold: float = 0.03  # 3% minimum improvement
    budget_limit_tokens: int = 50000
    budget_limit_usd: float = 50.0
    
    def improvement_rate(self) -> float:
        """Calculate improvement rate since last iteration"""
        if self.iteration == 0:
            return 0.0
        return self.score_improvement / max(1.0, self.score_improvement)


class AgentOptimizer:
    """
    Dynamically determines optimal number of agents based on:
    - Task complexity
    - Cost/quality trade-offs  
    - Convergence detection
    
    Reference: Hovsky et al. (2023) "Evaluating the Trade-offs of 
    Multi-Agent Competition in LLM Workflows"
    """
    
    # Saturation curve parameters from Hovsky et al.
    SATURATION_FACTOR = 0.7
    MAX_AGENTS_HARD_LIMIT = 5
    MIN_IMPROVEMENT_THRESHOLD = 0.03  # 3% minimum gain
    
    # Cost parameters (configurable)
    BASE_COST_PER_AGENT_TOKENS = 8000
    BASE_COST_PER_AGENT_USD = 3.0
    TOURNAMENT_OVERHEAD_FACTOR = 1.5
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.history: List[CompetitionMetrics] = []
        self._cost_params = self._load_cost_params()

    def _load_cost_params(self) -> Dict[str, float]:
        """Load cost parameters from config"""
        return {
            'tokens_per_agent': self.config.get('tokens_per_agent', self.BASE_COST_PER_AGENT_TOKENS),
            'usd_per_agent': self.config.get('usd_per_agent', self.BASE_COST_PER_AGENT_USD),
            'overhead_factor': self.config.get('overhead_factor', self.TOURNAMENT_OVERHEAD_FACTOR),
        }

    def _calculate_max_by_budget(self, budget_amount: float, unit_of_measure: str) -> int:
        """
        Generic budget-based agent limit calculation.
        
        Args:
            budget_amount: Budget in tokens or USD
            unit_of_measure: 'tokens' or 'usd'
            
        Returns:
            Maximum affordable agents
        """
        cost_per_agent = self._cost_params[f'{unit_of_measure}_per_agent']
        overhead = self._cost_params['overhead_factor']
        
        max_affordable = int(budget_amount / (cost_per_agent * overhead))
        return min(max_affordable, self.MAX_AGENTS_HARD_LIMIT)

    def calculate_optimal_agent_count(
        self,
        task_complexity: float = 0.5,
        budget_tokens: Optional[int] = None,
        budget_usd: Optional[float] = None,
        previous_improvements: Optional[List[float]] = None
    ) -> int:
        """
        Calculate optimal agent count based on task characteristics.
        
        Uses Hovsky et al.'s model: Performance Gain = 100 / (1 + e^(-k*(n-1)))
        """
        # Base decision on complexity
        if task_complexity < 0.3:
            base_agents = 2
        elif task_complexity < 0.7:
            base_agents = 3
        else:
            base_agents = 4
        
        # Adjust for budget constraints
        if budget_tokens:
            max_by_budget = self._calculate_max_by_budget(budget_tokens, 'tokens')
            base_agents = min(base_agents, max_by_budget)
        
        if budget_usd:
            max_by_cost = self._calculate_max_by_budget(budget_usd, 'usd')
            base_agents = min(base_agents, max_by_cost)
        
        # Check convergence history
        if previous_improvements and len(previous_improvements) >= 3:
            recent_gain = sum(previous_improvements[-3:]) / 3
            if recent_gain < self.MIN_IMPROVEMENT_THRESHOLD:
                base_agents = max(2, base_agents - 1)
        
        return min(max(base_agents, 2), self.MAX_AGENTS_HARD_LIMIT)

    def should_reduce_agents(self, metrics: CompetitionMetrics) -> bool:
        """
        Determine if we should reduce agent count based on metrics.
        Returns True if diminishing returns are detected.
        """
        if len(self.history) < 3:
            return False
        
        recent_scores = [h.best_score for h in self.history[-3:]]
        score_variance = max(recent_scores) - min(recent_scores)
        
        if score_variance < 0.02:
            return True
        
        budget_usd = self.config.get('budget_limit_usd', 50.0)
        if metrics.total_cost_usd > budget_usd:
            return True
        
        return False

    def estimate_performance_gain(self, agent_count: int) -> float:
        """
        Estimate performance gain using Hovsky et al.'s saturation curve.
        Gain = 100 / (1 + e^(-k*(n-1)))
        """
        import math
        
        if agent_count < 1:
            return 0.0
        
        k = self.SATURATION_FACTOR
        gain = 100 / (1 + math.exp(-k * (agent_count - 1)))
        
        return min(gain / 100, 1.0)

    def get_recommendation(self) -> Dict[str, any]:
        """Get current optimization recommendation"""
        if len(self.history) < 2:
            return {
                "agent_count": 3,
                "reason": "Initial recommendation",
                "expected_gain": self.estimate_performance_gain(3)
            }
        
        latest = self.history[-1]
        
        if self.should_reduce_agents(latest):
            new_count = max(2, latest.agent_count - 1)
            return {
                "agent_count": new_count,
                "reason": "Convergence detected - diminishing returns",
                "expected_gain": self.estimate_performance_gain(new_count)
            }
        
        current_gain = self.estimate_performance_gain(latest.agent_count)
        next_gain = self.estimate_performance_gain(latest.agent_count + 1)
        marginal_gain = next_gain - current_gain
        
        if marginal_gain < self.MIN_IMPROVEMENT_THRESHOLD:
            return {
                "agent_count": latest.agent_count,
                "reason": "Marginal gain below threshold",
                "expected_gain": current_gain
            }
        
        return {
            "agent_count": min(latest.agent_count + 1, self.MAX_AGENTS_HARD_LIMIT),
            "reason": "Marginal gain exceeds threshold",
            "expected_gain": next_gain
        }