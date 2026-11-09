"""Tests for the agent pool."""

import pytest

from openorchestra.core.agent_interface import AgentFactory
from openorchestra.core.agent_pool import AgentPool


def make_pool(**kwargs) -> AgentPool:
    return AgentFactory().create_pool(**kwargs)


async def test_pool_initialisation() -> None:
    pool = make_pool(pool_size=3)
    status = pool.get_pool_status()

    assert status["pool_size"] == 3
    assert status["available"] == 3
    assert status["in_use"] == 0
    assert status["healthy_available"] == 3


async def test_acquire_and_release() -> None:
    pool = make_pool(pool_size=2)
    agent = await pool.acquire_agent(timeout=0.1)

    assert agent is not None
    assert pool.get_pool_status()["available"] == 1
    assert pool.get_pool_status()["in_use"] == 1

    pool.release_agent(agent)
    assert pool.get_pool_status()["available"] == 2
    assert pool.get_pool_status()["in_use"] == 0


async def test_pool_creates_extra_agents_then_gives_up() -> None:
    pool = make_pool(pool_size=1)

    first = await pool.acquire_agent(timeout=0.1)
    second = await pool.acquire_agent(timeout=0.1)
    third = await pool.acquire_agent(timeout=0.01)

    assert first is not None
    assert second is not None
    assert third is None
    assert pool.get_metrics().cache_misses >= 1


async def test_unknown_agent_type_is_rejected() -> None:
    pool = make_pool(pool_size=1)
    with pytest.raises(ValueError, match="Unknown agent type"):
        await pool.acquire_agent(agent_type="nope", timeout=0.01)


async def test_execute_batch_returns_indexed_results() -> None:
    pool = make_pool(pool_size=3)
    results = await pool.execute_batch("do work", agent_count=3, timeout_per_agent=5)

    assert len(results) == 3
    assert [result["index"] for result in results] == [0, 1, 2]
    assert all(result["success"] for result in results)
    assert all("solution" in result for result in results)
    assert pool.get_pool_status()["available"] == 3


async def test_execute_batch_fills_missing_agents() -> None:
    pool = make_pool(pool_size=1)
    results = await pool.execute_batch("do work", agent_count=3, timeout_per_agent=5)

    assert len(results) == 3
    assert [result["success"] for result in results] == [True, True, False]
    assert "error" in results[2]


async def test_execute_batch_records_agent_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = make_pool(pool_size=1)
    agent = pool._available[0]

    async def boom(task, timeout=300):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "execute", boom)
    results = await pool.execute_batch("do work", agent_count=1, timeout_per_agent=1)

    assert results[0]["success"] is False
    assert "boom" in results[0]["error"]
    assert pool.get_metrics().errors == 1


async def test_health_check_covers_available_and_in_use() -> None:
    pool = make_pool(pool_size=2)
    await pool.acquire_agent(timeout=0.1)

    status = await pool.health_check()
    assert len(status) == 2
    assert all(status.values())


async def test_reset_restores_pool() -> None:
    pool = make_pool(pool_size=2)
    await pool.acquire_agent(timeout=0.1)
    pool.reset()

    status = pool.get_pool_status()
    assert status["available"] == 2
    assert status["in_use"] == 0


async def test_type_distribution_is_deterministic() -> None:
    pool = make_pool(
        pool_size=4,
        agent_type="opencode",
        agent_type_distribution={"opencode": 0.5, "autodev": 0.5},
    )

    types = [pool._available[index].get_type() for index in range(4)]
    assert types.count("opencode") == 2
    assert types.count("autodev") == 2


async def test_unhealthy_agent_is_replaced_on_release() -> None:
    pool = make_pool(pool_size=1)
    agent = await pool.acquire_agent(timeout=0.1)
    assert agent is not None
    agent._state.error_count = 99
    pool.release_agent(agent)

    assert pool.get_pool_status()["available"] == 1
    assert pool.get_pool_status()["healthy_available"] == 1
    assert pool.get_metrics().errors == 1
