"""End-to-end tests for the competition orchestrator."""

import pytest

from openorchestra.core.competition_orchestrator import (
    CompetitionConfig,
    CompetitionOrchestrator,
    CompetitionResult,
)

GOOD_SOLUTION = '''
import logging
from typing import Any


def create_user(db: Any, name: str) -> None:
    """Create a user safely."""
    if not name:
        raise ValueError("name required")
    query = "INSERT INTO users(name) VALUES (:name)"
    try:
        db.execute(query, {"name": name})
    except Exception:
        logging.exception("insert failed")
        raise


def test_create_user():
    assert create_user
'''

WEAK_SOLUTION = "print('todo')"


class FakeOpenCodeAdapter:
    def __init__(self, solutions: list[str] | None = None, error_for: set[str] | None = None):
        self.solutions = solutions or [GOOD_SOLUTION, WEAK_SOLUTION]
        self.error_for = error_for or set()
        self.calls: list[str] = []

    async def execute_skill_task(self, task: str, agent_id: str, timeout: int):
        self.calls.append(agent_id)
        if agent_id in self.error_for:
            raise RuntimeError(f"agent {agent_id} crashed")
        index = int(agent_id.split("_")[-1]) - 1
        solution = self.solutions[index % len(self.solutions)]
        return {
            "agent_id": agent_id,
            "solution": solution,
            "success": True,
            "execution_time": 0.1,
            "cost": {"USD": 0.01},
        }


class FakeAutoDevAdapter:
    def __init__(self, winner: str | None = "winner_agent", success: bool = True):
        self.winner = winner
        self.success = success

    async def run_tournament_async(self, task: str, domain: str, agent_count: int):
        return {"winner": self.winner, "success": self.success}


def make_orchestrator(memory, **kwargs) -> CompetitionOrchestrator:
    return CompetitionOrchestrator(memory=memory, **kwargs)


def make_config(**overrides) -> CompetitionConfig:
    values = {
        "domain": "backend",
        "task_description": "Create a safe user endpoint",
        "agent_count": 2,
        "use_opencode": True,
        "record_memory": False,
        "simulate": True,
    }
    values.update(overrides)
    return CompetitionConfig(**values)


async def test_dry_run_does_not_execute_agents(memory) -> None:
    orchestrator = make_orchestrator(memory)
    result = await orchestrator.run_competition(make_config(dry_run=True))

    assert result.winner is None
    assert len(result.agent_results) == 2
    assert result.patterns_learned == 0
    assert orchestrator.get_competition_history() == []


async def test_unknown_domain_is_rejected(memory) -> None:
    orchestrator = make_orchestrator(memory)
    with pytest.raises(ValueError, match="Unknown domain"):
        await orchestrator.run_competition(make_config(domain="nope"))


@pytest.mark.parametrize("agent_count", [0, 6])
async def test_invalid_agent_count_is_rejected(memory, agent_count: int) -> None:
    orchestrator = make_orchestrator(memory)
    with pytest.raises(ValueError, match="agent_count"):
        await orchestrator.run_competition(make_config(agent_count=agent_count))


async def test_simulated_competition_selects_a_winner(memory) -> None:
    orchestrator = make_orchestrator(memory)
    result = await orchestrator.run_competition(make_config())

    assert isinstance(result, CompetitionResult)
    assert result.winner in {"agent_1", "agent_2"}
    assert result.total_score > 0
    assert len(result.agent_results) == 2
    assert result.execution_time >= 0
    assert result.cost_estimate > 0


async def test_evaluation_ranks_better_solution_first(memory) -> None:
    orchestrator = make_orchestrator(memory)
    adapter = FakeOpenCodeAdapter([GOOD_SOLUTION, WEAK_SOLUTION])
    orchestrator._opencode_adapter = adapter

    result = await orchestrator.run_competition(make_config())

    assert result.winner == "agent_1"
    assert result.agent_results[0]["score"] > result.agent_results[1]["score"]
    assert result.total_score >= 0.7


async def test_failed_agent_is_skipped(memory) -> None:
    orchestrator = make_orchestrator(memory)
    orchestrator._opencode_adapter = FakeOpenCodeAdapter(
        [GOOD_SOLUTION, WEAK_SOLUTION], error_for={"agent_1"}
    )

    result = await orchestrator.run_competition(make_config())

    assert result.winner == "agent_2"
    assert result.agent_results[0]["success"] is False
    assert result.agent_results[0]["score"] == 0.0


async def test_all_failed_agents_produce_no_winner(memory) -> None:
    orchestrator = make_orchestrator(memory)
    orchestrator._opencode_adapter = FakeOpenCodeAdapter(
        [GOOD_SOLUTION, WEAK_SOLUTION], error_for={"agent_1", "agent_2"}
    )

    result = await orchestrator.run_competition(make_config())

    assert result.winner is None
    assert result.total_score == 0.0


async def test_optimizer_controls_agent_count(memory) -> None:
    orchestrator = make_orchestrator(memory)
    adapter = FakeOpenCodeAdapter([GOOD_SOLUTION])
    orchestrator._opencode_adapter = adapter

    result = await orchestrator.run_competition(make_config(optimize=True, task_complexity=0.9))

    assert len(result.agent_results) == 4
    assert len(adapter.calls) == 4


async def test_memory_is_recorded_and_used(memory) -> None:
    orchestrator = make_orchestrator(memory)
    result = await orchestrator.run_competition(make_config(record_memory=True))

    stats = memory.get_stats()
    assert stats["competitions_run"] == 1
    assert stats["patterns_stored"] > 0
    assert result.patterns_learned > 0

    prepared = await orchestrator._prepare_task(make_config())
    assert "LEARNED CONTEXT" in prepared


async def test_autodev_backend_is_supported(memory) -> None:
    orchestrator = make_orchestrator(memory)
    orchestrator._autodev_adapter = FakeAutoDevAdapter()

    result = await orchestrator.run_competition(
        make_config(use_opencode=False, use_autodev=True, agent_count=3)
    )

    assert result.winner == "autodev"
    assert len(result.agent_results) == 1
    assert result.total_score > 0


async def test_autodev_failure_is_reported(memory) -> None:
    orchestrator = make_orchestrator(memory)
    orchestrator._autodev_adapter = FakeAutoDevAdapter(winner=None, success=False)

    result = await orchestrator.run_competition(make_config(use_opencode=False, use_autodev=True))

    assert result.winner is None
    assert result.agent_results[0]["success"] is False


async def test_missing_backend_is_rejected(memory) -> None:
    orchestrator = make_orchestrator(memory)
    with pytest.raises(ValueError, match="backend"):
        await orchestrator.run_competition(make_config(use_opencode=False, use_autodev=False))


async def test_history_and_statistics(memory) -> None:
    orchestrator = make_orchestrator(memory)
    await orchestrator.run_competition(make_config(record_memory=False))
    await orchestrator.run_competition(make_config(record_memory=False, domain="qa_testing"))

    assert len(orchestrator.get_competition_history()) == 2
    assert len(orchestrator.get_competition_history(domain="backend")) == 1

    stats = orchestrator.get_statistics()
    assert stats["total_competitions_run"] == 2
    assert stats["domains_supported"] == 9
    assert stats["active_competitions"] == 2


async def test_history_domain_filter_returns_most_recent(memory) -> None:
    orchestrator = make_orchestrator(memory)
    for _ in range(3):
        await orchestrator.run_competition(make_config(record_memory=False))

    all_entries = orchestrator.get_competition_history(limit=10)
    filtered = orchestrator.get_competition_history(domain="backend", limit=2)

    assert [entry["id"] for entry in filtered] == [
        entry["id"] for entry in all_entries if entry["domain"] == "backend"
    ][-2:]


async def test_result_is_serialisable(memory) -> None:
    orchestrator = make_orchestrator(memory)
    result = await orchestrator.run_competition(make_config())

    data = result.to_dict()
    assert data["competition_id"] == result.competition_id
    assert data["winner"] == result.winner
    assert isinstance(data["agent_results"], list)
