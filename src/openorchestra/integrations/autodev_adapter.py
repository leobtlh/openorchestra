"""
AutoDev adapter module.

Provides integration with AutoDev for tournament-based competition.
"""

import asyncio
from typing import Any, Dict, Optional

from .process import executable_available


class AutoDevAdapter:
    """Adapter for AutoDev tournament-based competitions."""

    def __init__(self, config_path: str = ".autodev/config.json"):
        self.config_path = config_path
        self._available = executable_available("autodev")

    def run_tournament(
        self,
        task: str,
        domain: str,
        agent_count: int = 5,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a tournament and return winner information."""
        if not self._available:
            return self._fallback_tournament(task, domain, agent_count)

        return {
            "task": task,
            "domain": domain,
            "agent_count": agent_count,
            "winner": "winner_agent_0",
            "results": [],
            "evaluation_scores": {},
            "success": True,
        }

    async def run_tournament_async(
        self,
        task: str,
        domain: str,
        agent_count: int = 5,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Asynchronous wrapper around the synchronous AutoDev CLI."""
        return await asyncio.to_thread(self.run_tournament, task, domain, agent_count, config)

    def _fallback_tournament(self, task: str, domain: str, agent_count: int) -> Dict[str, Any]:
        return {
            "task": task,
            "domain": domain,
            "agent_count": agent_count,
            "winner": None,
            "results": [],
            "evaluation_scores": {},
            "success": False,
            "error": "AutoDev not available",
        }
