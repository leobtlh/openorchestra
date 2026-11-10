"""
Agent pool manager for OpenOrchestra.

Manages a pool of reusable agents for efficient competition execution.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .agent_interface import AgentFactory, AgentInterface

logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """Metrics for the agent pool."""

    total_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    average_wait_time: float = 0.0


class AgentPool:
    """Pool of agents for tournament execution."""

    def __init__(
        self,
        factory: AgentFactory,
        pool_size: int = 3,
        default_agent_type: str = "opencode",
        type_distribution: Optional[Dict[str, float]] = None,
    ):
        if pool_size < 1:
            raise ValueError("pool_size must be at least 1")

        self.factory = factory
        self._pool_size = pool_size
        self._default_agent_type = default_agent_type
        self._type_distribution = type_distribution or {default_agent_type: 1.0}
        self._type_plan = self._build_type_plan()

        self._available: List[AgentInterface] = []
        self._in_use: Dict[str, AgentInterface] = {}
        self._health_status: Dict[str, bool] = {}

        self._metrics = PoolMetrics()
        self._total_wait_time = 0.0
        self._wait_count = 0

        self._initialize_pool()

    def _build_type_plan(self) -> List[str]:
        distribution = {
            agent_type: weight
            for agent_type, weight in self._type_distribution.items()
            if weight > 0
        }
        if not distribution:
            distribution = {self._default_agent_type: 1.0}

        total = sum(distribution.values())
        plan: List[str] = []
        for index in range(self._pool_size):
            target = (index + 0.5) / self._pool_size * total
            cumulative = 0.0
            for agent_type, weight in distribution.items():
                cumulative += weight
                if target <= cumulative:
                    plan.append(agent_type)
                    break
            else:
                plan.append(self._default_agent_type)

        return plan

    def _initialize_pool(self) -> None:
        for index, agent_type in enumerate(self._type_plan):
            agent = self.factory.create_agent(agent_type, f"{agent_type}_pool_{index}")
            self._available.append(agent)
            self._health_status[agent.get_id()] = True
        logger.info("Initialized agent pool with %s agents", self._pool_size)

    def _max_size(self) -> int:
        return self._pool_size * 2

    def _total_agents(self) -> int:
        return len(self._available) + len(self._in_use)

    def _take_available(self, agent_type: str) -> Optional[AgentInterface]:
        for agent in self._available:
            if agent.get_type() == agent_type and agent.is_healthy():
                self._available.remove(agent)
                self._in_use[agent.get_id()] = agent
                return agent
        return None

    def _create_agent(self, agent_type: str) -> AgentInterface:
        agent = self.factory.create_agent(agent_type)
        self._in_use[agent.get_id()] = agent
        self._health_status[agent.get_id()] = True
        return agent

    async def acquire_agent(
        self, agent_type: Optional[str] = None, timeout: float = 30.0
    ) -> Optional[AgentInterface]:
        """Acquire an available agent, creating one while capacity remains."""
        start_wait = time.time()
        agent_type = agent_type or self._default_agent_type

        agent = self._take_available(agent_type)
        if agent is not None:
            self._metrics.cache_hits += 1
            return agent

        if self._total_agents() < self._max_size():
            self._metrics.cache_misses += 1
            return self._create_agent(agent_type)

        while time.time() - start_wait < timeout:
            await asyncio.sleep(0.01)
            agent = self._take_available(agent_type)
            if agent is not None:
                self._metrics.cache_hits += 1
                return agent
            if self._total_agents() < self._max_size():
                self._metrics.cache_misses += 1
                return self._create_agent(agent_type)

        self._metrics.cache_misses += 1
        self._total_wait_time += time.time() - start_wait
        self._wait_count += 1
        return None

    def release_agent(self, agent: AgentInterface) -> None:
        """Return a healthy agent to the pool, or replace an unhealthy one."""
        agent_id = agent.get_id()
        if agent_id not in self._in_use:
            return

        del self._in_use[agent_id]
        if agent.is_healthy():
            self._health_status[agent_id] = True
            self._available.append(agent)
            return

        self._health_status[agent_id] = False
        self._metrics.errors += 1
        logger.warning("Replacing unhealthy agent %s", agent_id)

        if self._total_agents() < self._pool_size:
            replacement = self.factory.create_agent(agent.get_type())
            self._available.append(replacement)
            self._health_status[replacement.get_id()] = True

    async def execute_batch(
        self, task: str, agent_count: int, timeout_per_agent: int = 300
    ) -> List[Dict[str, Any]]:
        """Execute the same task with multiple agents in parallel."""
        if agent_count < 1:
            raise ValueError("agent_count must be at least 1")

        self._metrics.total_operations += 1
        agents = await self._acquire_many(agent_count)

        results = await asyncio.gather(
            *[agent.execute(task, timeout_per_agent) for agent in agents],
            return_exceptions=True,
        )

        for agent in agents:
            self.release_agent(agent)

        processed = self._process_results(results)
        while len(processed) < agent_count:
            index = len(processed)
            processed.append(
                {
                    "success": False,
                    "solution": "",
                    "error": "No agent available",
                    "agent_id": f"unknown_{index}",
                    "index": index,
                }
            )
        return processed

    async def _acquire_many(self, agent_count: int) -> List[AgentInterface]:
        agents: List[AgentInterface] = []
        for _ in range(agent_count):
            agent = await self.acquire_agent(timeout=0.01)
            if agent is not None:
                agents.append(agent)

        if len(agents) < agent_count:
            logger.warning("Could only acquire %s of %s agents", len(agents), agent_count)
        return agents

    def _process_results(self, results: List[Any]) -> List[Dict[str, Any]]:
        processed: List[Dict[str, Any]] = []
        for index, result in enumerate(results):
            if isinstance(result, BaseException):
                self._metrics.errors += 1
                processed.append(
                    {
                        "success": False,
                        "solution": "",
                        "error": str(result),
                        "agent_id": f"unknown_{index}",
                        "index": index,
                    }
                )
            elif isinstance(result, dict):
                result["index"] = index
                processed.append(result)
            else:
                processed.append(
                    {
                        "success": False,
                        "solution": "",
                        "error": f"Invalid agent result: {type(result).__name__}",
                        "agent_id": f"unknown_{index}",
                        "index": index,
                    }
                )
        return processed

    def get_metrics(self) -> PoolMetrics:
        """Get pool performance metrics."""
        if self._wait_count > 0:
            self._metrics.average_wait_time = self._total_wait_time / self._wait_count
        return self._metrics

    def get_pool_status(self) -> Dict[str, Any]:
        """Get the current pool status."""
        healthy_available = sum(1 for agent in self._available if agent.is_healthy())
        unhealthy_available = len(self._available) - healthy_available

        return {
            "pool_size": self._pool_size,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "healthy_available": healthy_available,
            "unhealthy_available": unhealthy_available,
            "errors": self._metrics.errors,
            "metrics": self._metrics,
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check the health of every agent in the pool."""
        status = {agent.get_id(): agent.is_healthy() for agent in self._available}
        status.update({agent.get_id(): agent.is_healthy() for agent in self._in_use.values()})

        unhealthy = [agent_id for agent_id, healthy in status.items() if not healthy]
        if unhealthy:
            logger.warning("Unhealthy agents detected: %s", unhealthy)
        return status

    def reset(self) -> None:
        """Reset the pool, removing and recreating all agents."""
        self._available.clear()
        self._in_use.clear()
        self._health_status.clear()
        self._initialize_pool()
        logger.info("Agent pool reset")
