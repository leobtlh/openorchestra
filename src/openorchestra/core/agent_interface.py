"""
Agent interface and implementations for OpenOrchestra.

Provides an abstraction layer for different agent types (OpenCode, AutoDev, ...).
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from openorchestra.integrations.opencode_adapter import OpenCodeAdapter

    from .agent_pool import AgentPool


@dataclass
class AgentState:
    """State information for an agent."""

    agent_id: str
    is_available: bool = True
    last_used: Optional[float] = None
    error_count: int = 0
    total_executions: int = 0
    started_at: Optional[float] = None


class AgentInterface(ABC):
    """Abstract contract shared by every agent implementation."""

    @abstractmethod
    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a task and return a result dictionary."""

    @abstractmethod
    def get_id(self) -> str:
        """Return the unique agent identifier."""

    @abstractmethod
    def get_type(self) -> str:
        """Return the agent type identifier."""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Return True when the agent is operational."""

    @abstractmethod
    def get_state(self) -> AgentState:
        """Return the current agent state."""


class OpenCodeAgent(AgentInterface):
    """OpenCode-backed agent used by the pool."""

    def __init__(
        self,
        agent_id: str,
        opencode_path: str = "opencode",
        simulate: Optional[bool] = None,
        **config: Any,
    ):
        self._agent_id = agent_id
        self._opencode_path = opencode_path
        self._config = config
        self._state = AgentState(agent_id=agent_id, started_at=time.time())
        self._adapter: Optional["OpenCodeAdapter"] = None

        try:
            from openorchestra.integrations.opencode_adapter import OpenCodeAdapter

            self._adapter = OpenCodeAdapter(opencode_path, simulate=simulate)
            self._adapter_available = self._adapter.available or self._adapter.simulate
        except ImportError:
            self._adapter = None
            self._adapter_available = False

    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a task through the OpenCode adapter."""
        start_time = time.time()

        if self._adapter is None or not self._adapter_available:
            return {
                "success": False,
                "solution": "",
                "error": "OpenCode adapter not available",
                "agent_id": self._agent_id,
            }

        try:
            result = await asyncio.wait_for(
                self._adapter.execute_skill_task(task, self._agent_id, timeout),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": f"Timeout after {timeout}s",
                "agent_id": self._agent_id,
            }
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": str(exc),
                "agent_id": self._agent_id,
            }

        self._state.total_executions += 1
        self._state.last_used = time.time()
        return {
            "success": bool(result.get("success", True)),
            "solution": result.get("solution", ""),
            "execution_time": result.get("execution_time", time.time() - start_time),
            "cost": result.get("cost", {"USD": 0.0}),
            "agent_id": self._agent_id,
            "metadata": result,
        }

    def get_id(self) -> str:
        return self._agent_id

    def get_type(self) -> str:
        return "opencode"

    def is_healthy(self) -> bool:
        return self._adapter_available and self._state.error_count < 5

    def get_state(self) -> AgentState:
        return self._state


class AutoDevAgent(AgentInterface):
    """AutoDev-backed agent used by the pool."""

    def __init__(self, agent_id: str, **config: Any):
        self._agent_id = agent_id
        self._config = config
        self._state = AgentState(agent_id=agent_id, started_at=time.time())

        from openorchestra.integrations.autodev_adapter import AutoDevAdapter

        self._adapter = AutoDevAdapter()

    async def execute(self, task: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a tournament through the AutoDev adapter."""
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._adapter.run_tournament_async(task, "default", 1),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": f"Timeout after {timeout}s",
                "agent_id": self._agent_id,
            }
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._state.error_count += 1
            return {
                "success": False,
                "solution": "",
                "error": str(exc),
                "agent_id": self._agent_id,
            }

        winner = result.get("winner")
        success = bool(result.get("success")) and winner not in (None, "", "none")
        self._state.total_executions += 1
        self._state.last_used = time.time()

        return {
            "success": success,
            "solution": str(winner) if success else "",
            "execution_time": time.time() - start_time,
            "cost": {"USD": 0.0},
            "agent_id": self._agent_id,
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
    """Create agents of the requested type, decoupled from pool management."""

    def __init__(self, opencode_path: str = "opencode", simulate: Optional[bool] = True):
        self.opencode_path = opencode_path
        self.simulate = simulate

    def create_agent(self, agent_type: str, agent_id: Optional[str] = None) -> AgentInterface:
        """Create an agent of the specified type."""
        if agent_id is None:
            agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"

        if agent_type == "opencode":
            return OpenCodeAgent(agent_id, self.opencode_path, simulate=self.simulate)
        if agent_type == "autodev":
            return AutoDevAgent(agent_id)
        raise ValueError(f"Unknown agent type: {agent_type}")

    def create_pool(
        self,
        pool_size: int = 3,
        agent_type: str = "opencode",
        agent_type_distribution: Optional[Dict[str, float]] = None,
    ) -> "AgentPool":
        """Create a configured agent pool."""
        from .agent_pool import AgentPool

        return AgentPool(
            factory=self,
            pool_size=pool_size,
            default_agent_type=agent_type,
            type_distribution=agent_type_distribution or {agent_type: 1.0},
        )
