"""Tests for the dynamic agent optimizer."""

import pytest

from openorchestra.core.optimizer import AgentOptimizer, CompetitionMetrics


@pytest.mark.parametrize(
    ("complexity", "expected"),
    [(0.2, 2), (0.5, 3), (0.9, 4)],
)
def test_complexity_mapping(complexity: float, expected: int) -> None:
    assert AgentOptimizer().calculate_optimal_agent_count(task_complexity=complexity) == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    [({}, 4), ({"max_agents": 5}, 5), ({"max_agents": 99}, 5), ({"max_agents": 1}, 1)],
)
def test_default_max_agents_is_configurable(config: dict, expected: int) -> None:
    assert AgentOptimizer(config).max_agents == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"budget_tokens": 13000}, 1),
        ({"budget_tokens": 25000}, 2),
        ({"budget_tokens": 100000}, 3),
        ({"budget_usd": 5}, 1),
        ({"budget_usd": 10}, 2),
        ({"budget_usd": 100}, 3),
        ({"budget_tokens": 0}, 1),
        ({"budget_usd": 0}, 1),
    ],
)
def test_budgets_limit_agent_count(kwargs: dict, expected: int) -> None:
    assert AgentOptimizer().calculate_optimal_agent_count(**kwargs) == expected


def test_malformed_config_values_fall_back_to_defaults() -> None:
    optimizer = AgentOptimizer(
        {
            "max_agents": "lots",
            "min_improvement_threshold": "not-a-number",
            "tokens_per_agent": None,
            "usd_per_agent": "free",
            "overhead_factor": [],
        }
    )

    assert optimizer.max_agents == AgentOptimizer.DEFAULT_MAX_AGENTS
    assert optimizer.min_improvement_threshold == AgentOptimizer.MIN_IMPROVEMENT_THRESHOLD
    assert (
        optimizer.calculate_optimal_agent_count(
            task_complexity=0.9, budget_tokens=1_000_000, budget_usd=1_000
        )
        == 4
    )


def test_convergence_reduces_agent_count() -> None:
    optimizer = AgentOptimizer()
    count = optimizer.calculate_optimal_agent_count(
        task_complexity=0.9,
        previous_improvements=[0.01, 0.02, 0.01],
    )
    assert count == 3


def test_performance_gain_curve() -> None:
    optimizer = AgentOptimizer()

    assert optimizer.estimate_performance_gain(0) == 0.0
    assert optimizer.estimate_performance_gain(1) == pytest.approx(0.5)
    gains = [optimizer.estimate_performance_gain(n) for n in range(1, 6)]
    assert gains == sorted(gains)
    assert gains[-1] < 1.0
    assert optimizer.estimate_performance_gain(3) == pytest.approx(0.8022, abs=0.001)


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        (CompetitionMetrics(), 0.0),
        (CompetitionMetrics(iteration=1, best_score=0.8, score_improvement=0.1), 0.125),
    ],
)
def test_improvement_rate(metrics: CompetitionMetrics, expected: float) -> None:
    assert metrics.improvement_rate() == pytest.approx(expected)


def test_should_reduce_agents_on_convergence() -> None:
    optimizer = AgentOptimizer()
    optimizer.history = [
        CompetitionMetrics(iteration=i, best_score=score)
        for i, score in enumerate([0.80, 0.81, 0.805, 0.806])
    ]
    assert optimizer.should_reduce_agents(optimizer.history[-1]) is True


def test_should_reduce_agents_on_budget() -> None:
    optimizer = AgentOptimizer()
    optimizer.history = [
        CompetitionMetrics(iteration=i, best_score=score) for i, score in enumerate([0.1, 0.5, 0.9])
    ]
    assert optimizer.should_reduce_agents(CompetitionMetrics(total_cost_usd=60.0)) is True


def test_recommendation_initial_and_growth() -> None:
    optimizer = AgentOptimizer()
    assert optimizer.get_recommendation()["agent_count"] == 3

    optimizer.history = [CompetitionMetrics(iteration=1, agent_count=2, best_score=0.5)]
    recommendation = optimizer.get_recommendation()
    assert recommendation["agent_count"] in (2, 3)
    assert recommendation["expected_gain"] > 0


def test_recommendation_stops_at_max() -> None:
    optimizer = AgentOptimizer()
    optimizer.history = [CompetitionMetrics(iteration=1, agent_count=4, best_score=0.95)]
    assert optimizer.get_recommendation()["agent_count"] == 4
