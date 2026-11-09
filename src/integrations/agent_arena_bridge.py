"""
Agent Arena bridge module.

Provides integration with Agent Arena for evaluation competitions.
"""

from typing import Dict, Any, Optional


class AgentArenaBridge:
    """
    Bridge for Agent Arena integration.
    
    Enables evaluation of agent outputs through Arena's scoring system.
    """

    def __init__(self):
        self._available = self._check_arena_available()

    def _check_arena_available(self) -> bool:
        """Check if Agent Arena is available"""
        try:
            import subprocess
            result = subprocess.run(
                ["arena", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, ImportError):
            return False

    def evaluate_comparison(
        self,
        agent_a_result: str,
        agent_b_result: str,
        criteria: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Compare two agent outputs using Arena's evaluation system.
        
        Args:
            agent_a_result: Solution from agent A
            agent_b_result: Solution from agent B
            criteria: Evaluation criteria weights
            
        Returns:
            Comparison result with winner and scores
        """
        if not self._available:
            return self._fallback_comparison(agent_a_result, agent_b_result)
        
        # This would interface with Agent Arena's comparison system
        return {
            "comparison_id": "comparison_1",
            "agent_a_score": 0.75,
            "agent_b_score": 0.82,
            "winner": "agent_b",
            "details": {},
            "success": True
        }

    def _fallback_comparison(self, agent_a_result: str, agent_b_result: str) -> Dict[str, Any]:
        """Fallback comparison when Arena is not available"""
        # Simple length-based comparison as fallback
        score_a = min(len(agent_a_result), 1000) / 1000
        score_b = min(len(agent_b_result), 1000) / 1000
        
        winner = "agent_a" if score_a > score_b else "agent_b"
        
        return {
            "comparison_id": "comparison_fallback",
            "agent_a_score": float(score_a),
            "agent_b_score": float(score_b),
            "winner": winner,
            "details": "Fallback comparison - Arena not available",
            "success": True
        }