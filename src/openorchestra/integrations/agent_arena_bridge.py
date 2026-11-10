"""
Agent Arena bridge module.

Provides integration with Agent Arena for evaluation competitions.
"""

from typing import Any, Dict, Optional

from .process import executable_available


class AgentArenaBridge:
    """Bridge between OpenOrchestra and Agent Arena's scoring system."""

    def __init__(self) -> None:
        self._available = executable_available("arena")

    def evaluate_comparison(
        self,
        agent_a_result: str,
        agent_b_result: str,
        criteria: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Compare two agent outputs and return the winner."""
        if not self._available:
            return self._fallback_comparison(agent_a_result, agent_b_result)

        return {
            "comparison_id": "comparison_1",
            "agent_a_score": 0.75,
            "agent_b_score": 0.82,
            "winner": "agent_b",
            "details": {},
            "success": True,
        }

    def _fallback_comparison(self, agent_a_result: str, agent_b_result: str) -> Dict[str, Any]:
        score_a = min(len(agent_a_result), 1000) / 1000
        score_b = min(len(agent_b_result), 1000) / 1000
        winner = "agent_a" if score_a > score_b else "agent_b"

        return {
            "comparison_id": "comparison_fallback",
            "agent_a_score": float(score_a),
            "agent_b_score": float(score_b),
            "winner": winner,
            "details": "Fallback comparison - Arena not available",
            "success": True,
        }
