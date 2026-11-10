"""Tests for agent abstractions and the agent factory."""

import asyncio

import pytest

from openorchestra.core.agent_interface import (
    AgentFactory,
    AutoDevAgent,
    OpenCodeAgent,
)
from openorchestra.core.agent_pool import AgentPool


def test_factory_creates_supported_agents() -> None:
    factory = AgentFactory()
    opencode = factory.create_agent("opencode", "agent_a")
    autodev = factory.create_agent("autodev", "agent_b")

    assert isinstance(opencode, OpenCodeAgent)
    assert isinstance(autodev, AutoDevAgent)
    assert opencode.get_id() == "agent_a"
    assert opencode.get_type() == "opencode"
    assert autodev.get_type() == "autodev"


def test_factory_rejects_unknown_agent_type() -> None:
    with pytest.raises(ValueError, match="Unknown agent type"):
        AgentFactory().create_agent("nope")


def test_generated_ids_are_unique() -> None:
    factory = AgentFactory()
    ids = {factory.create_agent("opencode").get_id() for _ in range(50)}
    assert len(ids) == 50


def test_factory_creates_pool() -> None:
    pool = AgentFactory().create_pool(pool_size=2)
    assert isinstance(pool, AgentPool)
    assert pool.get_pool_status()["pool_size"] == 2


async def test_opencode_agent_executes_simulated_task() -> None:
    agent = OpenCodeAgent("agent_1", simulate=True)
    result = await agent.execute("write a function", timeout=5)

    assert result["success"] is True
    assert result["agent_id"] == "agent_1"
    assert "write a function" in result["solution"]
    assert agent.get_state().total_executions == 1


async def test_opencode_agent_timeout_marks_error() -> None:
    agent = OpenCodeAgent("agent_1", simulate=True)

    async def slow(*args, **kwargs):
        await asyncio.sleep(1)

    agent._adapter.execute_skill_task = slow  # type: ignore[method-assign]
    result = await agent.execute("task", timeout=0.01)

    assert result["success"] is False
    assert "Timeout" in result["error"]
    assert agent.get_state().error_count == 1


def test_opencode_agent_becomes_unhealthy_after_errors() -> None:
    agent = OpenCodeAgent("agent_1", simulate=True)
    agent._state.error_count = 5
    assert agent.is_healthy() is False


async def test_autodev_agent_executes_tournament(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tournament(self, task, domain, agent_count=5, config=None):
        return {"winner": "agent_7", "success": True}

    monkeypatch.setattr(
        "openorchestra.integrations.autodev_adapter.AutoDevAdapter.run_tournament_async",
        fake_tournament,
    )

    result = await AutoDevAgent("agent_1").execute("task", timeout=5)
    assert result["success"] is True
    assert result["solution"] == "agent_7"


async def test_autodev_agent_treats_fallback_as_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fallback(self, task, domain, agent_count=5, config=None):
        return {"winner": None, "success": False, "error": "unavailable"}

    monkeypatch.setattr(
        "openorchestra.integrations.autodev_adapter.AutoDevAdapter.run_tournament_async",
        fallback,
    )

    result = await AutoDevAgent("agent_1").execute("task", timeout=5)
    assert result["success"] is False
