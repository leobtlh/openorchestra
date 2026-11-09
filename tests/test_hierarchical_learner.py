"""Tests for the hierarchical learner."""

from openorchestra.core.hierarchical_learner import HierarchicalLearner, propagate_domain_pattern
from openorchestra.core.pattern_signature import PatternSignature


def test_winning_pattern_is_stored() -> None:
    learner = HierarchicalLearner()
    signature = learner.learn_from_competition(
        domain="backend",
        agent_id="agent_1",
        pattern_type="security",
        solution="use parameterized queries",
        score=0.9,
        is_winning=True,
    )

    assert len(signature) == 12
    assert "backend" in learner.domain_knowledge
    assert signature in learner.domain_knowledge["backend"]["patterns"]
    assert learner.domain_knowledge["backend"]["performance_metrics"] == [0.9]


def test_non_winning_pattern_creates_domain_entry() -> None:
    learner = HierarchicalLearner()
    signature = learner.learn_from_competition(
        domain="qa_testing",
        agent_id="agent_2",
        pattern_type="tests",
        solution="add assertions",
        score=0.4,
    )

    assert signature in learner.domain_knowledge["qa_testing"]["patterns"]
    assert signature in learner.global_patterns


def test_pattern_becomes_global_after_three_occurrences() -> None:
    learner = HierarchicalLearner()
    for _ in range(3):
        signature = learner.learn_from_competition(
            domain="backend",
            agent_id="agent_1",
            pattern_type="security",
            solution="use parameterized queries",
            score=0.8,
            is_winning=True,
        )

    assert signature in learner.global_patterns


def test_learning_pattern_can_later_become_a_winner() -> None:
    learner = HierarchicalLearner()
    signature = learner.learn_from_competition(
        domain="backend",
        agent_id="agent_1",
        pattern_type="security",
        solution="use parameterized queries",
        score=0.4,
        is_winning=False,
    )

    learner.learn_from_competition(
        domain="backend",
        agent_id="agent_1",
        pattern_type="security",
        solution="use parameterized queries",
        score=0.9,
        is_winning=True,
    )

    pattern = learner.domain_knowledge["backend"]["patterns"][signature]
    assert pattern["score_history"] == [0.9]
    assert pattern["confidence"] > 0.5


def test_winner_is_not_downgraded_by_later_learning_pattern() -> None:
    learner = HierarchicalLearner()
    signature = learner.learn_from_competition(
        domain="backend",
        agent_id="agent_1",
        pattern_type="security",
        solution="use parameterized queries",
        score=0.9,
        is_winning=True,
    )

    learner.learn_from_competition(
        domain="backend",
        agent_id="agent_2",
        pattern_type="security",
        solution="use parameterized queries",
        score=0.2,
        is_winning=False,
    )

    pattern = learner.domain_knowledge["backend"]["patterns"][signature]
    assert pattern["confidence"] == 0.8
    assert pattern["score_history"] == [0.9]


def test_relevant_patterns_are_returned() -> None:
    learner = HierarchicalLearner()
    learner.learn_from_competition(
        "backend", "agent_1", "security", "validate input", 0.9, is_winning=True
    )

    query = PatternSignature.from_context("backend", "security", "validate input")
    results = learner.get_relevant_patterns(query)

    assert results
    assert results[0]["similarity"] >= 0.7


def test_history_is_bounded() -> None:
    learner = HierarchicalLearner()
    for index in range(1100):
        learner.learn_from_competition("backend", "agent", "general", f"solution {index}", 0.1)

    assert len(learner.pattern_history) <= 1000


def test_propagate_domain_pattern_helper() -> None:
    assert set(propagate_domain_pattern({"a"}, ["b", "a"])) == {"a", "b"}
