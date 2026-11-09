"""
Agent pool manager for OpenOrchestra.

Manages a pool of reusable agents for efficient competition execution.
"""

import asyncio
import time
from typing import Optional, Dict, List, Any
from collections import defaultdict
from dataclasses import dataclass
import logging

from .agent_interface import AgentInterface, AgentFactory, AgentState

logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """Metrics for the agent pool"""
    total_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    average_wait_time: float = 0.0


class AgentPool:
    """
    Pool of agents for tournament execution.
    
    Manages agent lifecycle, health, and efficient reuse.
    """

    def __init__(
        self,
        factory: AgentFactory,
        pool_size: int = 3,
        default_agent_type: str = "opencode",
        type_distribution: Optional[Dict[str, float]] = None
    ):
        self.factory = factory
        self._pool_size = pool_size
        self._default_agent_type = default_agent_type
        self._type_distribution = type_distribution or {default_agent_type: 1.0}
        
        # Agent storage
        self._available: List[AgentInterface] = []
        self._in_use: Dict[str, AgentInterface] = {}
        self._health_status: Dict[str, bool] = {}
        
        # Metrics
        self._metrics = PoolMetrics()
        self._total_wait_time = 0.0
        self._wait_count = 0
        
        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Create initial set of agents"""
        for i in range(self._pool_size):
            agent_type = self._get_agent_type(i)
            agent_id = f"{agent_type}_pool_{i}"
            
            agent = self.factory.create_agent(agent_type, agent_id)
            self._available.append(agent)
            self._health_status[agent_id] = True
            
        logger.info(f"Initialized agent pool with {self._pool_size} agents")

    def _get_agent_type(self, index: int) -> str:
        """Determine agent type based on distribution"""
        if not self._type_distribution:
            return self._default_agent_type
            
        total = sum(self._type_distribution.values())
        target = (index % self._pool_size) / self._pool_size * total
        
        cumulative = 0.0
        for agent_type, weight in self._type_distribution.items():
            cumulative += weight
            if index % self._pool_size / self._pool_size <= cumulative / total:
                return agent_type
                
        return self._default_agent_type

    async def acquire_agent(
        self,
        agent_type: Optional[str] = None,
        timeout: float = 30.0
    ) -> Optional[AgentInterface]:
        """
        Acquire an available agent from the pool.
        
        Waits up to timeout seconds for an agent to become available.
        """
        start_wait = time.time()
        agent_type = agent_type or self._default_agent_type
        
        # Try to get an available agent immediately
        for agent in self._available:
            if agent.get_type() == agent_type and agent.is_healthy():
                self._available.remove(agent)
                self._in_use[agent.get_id()] = agent
                self._metrics.cache_hits += 1
                return agent
        
        # Wait for agent to become available
        wait_start = time.time()
        while time.time() - wait_start < timeout:
            await asyncio.sleep(0.1)
            
            for agent in self._available[:]:  # Copy for safe iteration
                if agent.get_type() == agent_type and agent.is_healthy():
                    self._available.remove(agent)
                    self._in_use[agent.get_id()] = agent
                    self._metrics.cache_hits += 1
                    return agent
        
        self._metrics.cache_misses += 1
        wait_time = time.time() - start_wait
        self._total_wait_time += wait_time
        self._wait_count += 1
        
        # Create new agent if pool exhausted
        if len(self._in_use) < self._pool_size * 2:  # Allow 2x pool size in use
            agent = self.factory.create_agent(agent_type)
            self._in_use[agent.get_id()] = agent
            logger.warning(f"Created new agent {agent.get_id()} due to pool exhaustion")
            return agent
        
        return None

    def release_agent(self, agent: AgentInterface) -> None:
        """Return an agent to the available pool"""
        agent_id = agent.get_id()
        
        if agent_id in self._in_use:
            del self._in_use[agent_id]
            self._available.append(agent)
            logger.debug(f"Released agent {agent_id} back to pool")
            
            # If agent had errors, mark for potential replacement
            if not agent.is_healthy():
                self._health_status[agent_id] = False

    async def execute_batch(
        self,
        task: str,
        agent_count: int,
        timeout_per_agent: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Execute the same task with multiple agents in parallel.
        
        Returns list of results in order.
        """
        self._metrics.total_operations += 1
        
        # Acquire agents
        agents = []
        acquisitions = []
        
        for i in range(agent_count):
            agent = await self.acquire_agent(timeout=10.0)
            if agent:
                agents.append(agent)
                acquisitions.append(i)
        
        if len(agents) < agent_count:
            logger.warning(f"Could only acquire {len(agents)} of {agent_count} agents")
        
        # Execute tasks in parallel
        results = await asyncio.gather(
            *[agent.execute(task, timeout_per_agent) for agent in agents],
            return_exceptions=True
        )
        
        # Release agents
        for agent in agents:
            self.release_agent(agent)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "solution": "",
                    "error": str(result),
                    "agent_id": f"unknown_{i}",
                    "index": i
                })
            else:
                result["index"] = i
                processed_results.append(result)
        
        return processed_results

    def get_metrics(self) -> PoolMetrics:
        """Get pool performance metrics"""
        if self._wait_count > 0:
            self._metrics.average_wait_time = self._total_wait_time / self._wait_count
        return self._metrics

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status"""
        healthy_available = sum(1 for a in self._available if a.is_healthy())
        unhealthy_available = sum(1 for a in self._available if not a.is_healthy())
        
        return {
            "pool_size": self._pool_size,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "healthy_available": healthy_available,
            "unhealthy_available": unhealthy_available,
            "errors": self._metrics.errors,
            "metrics": self._metrics
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all agents in pool"""
        status = {}
        
        for agent in self._available:
            status[agent.get_id()] = agent.is_healthy()
        
        for agent in self._in_use.values():
            status[agent.get_id()] = agent.is_healthy()
        
        unhealthy = [aid for aid, healthy in status.items() if not healthy]
        if unhealthy:
            logger.warning(f"Unhealthy agents detected: {unhealthy}")
        
        return status

    def reset(self) -> None:
        """Reset the pool, removing all agents"""
        self._available.clear()
        self._in_use.clear()
        self._initialize_pool()
        logger.info("Agent pool reset")