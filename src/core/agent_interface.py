"""
Agent interface and implementations for OpenOrchestra.

Provides abstraction layer for different agent types (OpenCode, AutoDev, etc.)
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentState:
    """State information for an agent"""
    agent_id: str
    is_available: bool = True
    last_used: Optional[float] = None
    error_count: int = 0
    total_executions: int = 0
    started_at: Optional[float] = None


class AgentInterface(ABC):
    """
    Abstract base class defining the agent contract.
    
    All agents in the pool must implement this interface.
    """

    @abstractmethod
    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute a task and return the result.
        
        Args:
            task: The task description to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict with keys: success, solution, execution_time, cost, error
        """
        pass

    @abstractmethod
    def get_id(self) -> str:
        """Return unique agent identifier"""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """Return agent type identifier"""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if agent is operational"""
        pass

    @abstractmethod
    def get_state(self) -> AgentState:
        """Get current agent state"""
        pass


class OpenCodeAgent(AgentInterface):
    """
    OpenCode-specific agent implementation.
    
    Wraps OpenCodeAdapter for competition use.
    """

    def __init__(self, agent_id: str, opencode_path: str = "opencode", **config):
        self._agent_id = agent_id
        self._opencode_path = opencode_path
        self._config = config
        
        # State tracking
        self._state = AgentState(
            agent_id=agent_id,
            started_at=time.time()
        )
        
        # Dynamic import to avoid hard dependency
        try:
            from openorchestra.integrations.opencode_adapter import OpenCodeAdapter
            self._adapter = OpenCodeAdapter(opencode_path)
            self._adapter_available = True
        except ImportError:
            self._adapter_available = False

    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute task via OpenCode adapter"""
        start_time = time.time()
        
        try:
            if not self._adapter_available:
                return {
                    "success": False,
                    "solution": "",
                    "error": "OpenCode adapter not available",
                    "agent_id": self._agent_id
                }
            
            # Use async execution with timeout
            result = await asyncio.wait_for(
                self._adapter.execute_skill_task(task, self._agent_id, timeout),
                timeout=timeout
            )
            
            self._state.total_executions += 1
            self._state.last_used = time.time()
            
            return {
                "success": result.get("success", True),
                "solution": result.get("solution", ""),
                "execution_time": result.get("execution_time", time.time() - start_time),
                "cost": result.get("cost", {"USD": 0.0}),
                "agent_id": self._agent_id,
                "metadata": result
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "solution": "",
                "error": f"Timeout after {timeout}s",
                "agent_id": self._agent_id
            }
        except Exception as e:
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": str(e),
                "agent_id": self._agent_id
            }

    def get_id(self) -> str:
        return self._agent_id

    def get_type(self) -> str:
        return "opencode"

    def is_healthy(self) -> bool:
        """Agent is healthy if adapter is available and not in error state"""
        return (
            self._adapter_available and
            self._state.error_count < 5  # Max 5 errors before unhealthy
        )

    def get_state(self) -> AgentState:
        return self._state


class AutoDevAgent(AgentInterface):
    """AutoDev-specific agent implementation"""

    def __init__(self, agent_id: str, **config):
        self._agent_id = agent_id
        self._config = config
        self._state = AgentState(agent_id=agent_id, started_at=time.time())

    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute via AutoDev adapter"""
        start_time = time.time()
        
        try:
            from openorchestra.integrations.autodev_adapter import AutoDevAdapter
            adapter = AutoDevAdapter()
            
            # Run tournament
            result = await asyncio.wait_for(
                adapter.run_tournament(task, "default", 1),
                timeout=timeout
            )
            
            self._state.total_executions += 1
            self._state.last_used = time.time()
            
            return {
                "success": result.get("winner") is not None,
                "solution": result.get("winner") or "",
                "execution_time": time.time() - start_time,
                "cost": {"USD": 0.0},
                "agent_id": self._agent_id
            }
        except Exception as e:
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": str(e),
                "agent_id": self._agent_id
            }

    def get_id(self) -> str:
        return self._agent_id

    def get_type(self) -> str:
        return "autodev"

    def is_healthy(self) -> bool:
        return self._state.error_count < 10

    def get_state(self) -> AgentState:
        return self._state


class AgentFactory:
    """
    Factory for creating different agent types.
    
    Decouples agent creation from pool management.
    """

    def __init__(self, opencode_path: str = "opencode"):
        self.opencode_path = opencode_path

    def create_agent(self, agent_type: str, agent_id: Optional[str] = None) -> AgentInterface:
        """Create an agent of the specified type"""
        if agent_id is None:
            agent_id = f"{agent_type}_{int(time.time() * 1000) % 10000}"

        if agent_type == "opencode":
            return OpenCodeAgent(agent_id, self.opencode_path)
        elif agent_type == "autodev":
            return AutoDevAgent(agent_id)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def create_pool(
        self,
        pool_size: int = 3,
        agent_type: str = "opencode",
        agent_type_distribution: Optional[Dict[str, float]] = None
    ) -> "AgentPool":
        """Create a configured agent pool"""
        return AgentPool(
            factory=self,
            pool_size=pool_size,
            default_agent_type=agent_type,
            type_distribution=agent_type_distribution or {agent_type: 1.0}
        )