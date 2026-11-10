"""Tests for the quality evaluator."""

import pytest

from openorchestra.evaluators.quality_evaluator import QualityEvaluator

GOOD_SOLUTION = '''
import logging


def create_user(db, name: str) -> None:
    """Create a user with validation."""
    if not name:
        raise ValueError("name is required")
    query = "INSERT INTO users(name) VALUES (:name)"
    try:
        db.execute(query, {"name": name})
    except Exception:
        logging.exception("insert failed")
        raise
'''

WEAK_SOLUTION = "print('hello')"


def test_weighted_average(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluator = QualityEvaluator()
    scores = {"code_quality": 1.0, "test_coverage": 0.0}
    monkeypatch.setattr(
        evaluator, "_evaluate_criterion", lambda criterion, solution, domain: scores[criterion]
    )

    result = evaluator.evaluate(
        solution="x",
        agent_id="agent_1",
        domain="backend",
        criteria={"code_quality": 0.75, "test_coverage": 0.25},
    )

    assert result.total_score == pytest.approx(0.75)
    assert result.criteria_scores == scores
    assert result.passed is True


def test_legacy_list_criteria_are_accepted() -> None:
    result = QualityEvaluator().evaluate(
        solution=GOOD_SOLUTION,
        agent_id="agent_1",
        domain="backend",
        criteria=[{"code_quality": 0.6}, {"test_coverage": 0.4}],
    )

    assert result.criteria_scores.keys() == {"code_quality", "test_coverage"}
    assert 0.0 <= result.total_score <= 1.0


def test_non_positive_weights_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluator = QualityEvaluator()
    monkeypatch.setattr(
        evaluator,
        "_evaluate_criterion",
        lambda criterion, solution, domain: 1.0 if criterion == "good" else 0.0,
    )

    result = evaluator.evaluate(
        solution="x",
        agent_id="agent_1",
        domain="backend",
        criteria={"good": 2.0, "negative": -1.0, "zero": 0.0},
    )

    assert result.criteria_scores == {"good": 1.0}
    assert result.total_score == pytest.approx(1.0)


def test_empty_criteria_scores_zero() -> None:
    result = QualityEvaluator().evaluate("code", "agent_1", "backend", {})
    assert result.total_score == 0.0
    assert result.passed is False


def test_empty_solution_scores_zero() -> None:
    result = QualityEvaluator().evaluate("   ", "agent_1", "backend", {"code_quality": 1.0})
    assert result.total_score == 0.0
    assert result.passed is False


def test_good_solution_beats_weak_solution() -> None:
    evaluator = QualityEvaluator()
    criteria = {"code_quality": 0.5, "security_standards": 0.5}

    good = evaluator.evaluate(GOOD_SOLUTION, "agent_1", "backend", criteria)
    weak = evaluator.evaluate(WEAK_SOLUTION, "agent_2", "backend", criteria)

    assert good.total_score > weak.total_score + 0.1
    assert good.passed is True
    assert weak.passed is False


def test_unknown_criterion_is_neutral() -> None:
    result = QualityEvaluator().evaluate("code", "agent_1", "backend", {"unknown_metric": 1.0})
    assert result.total_score == pytest.approx(0.5)


def test_details_include_domain_and_size() -> None:
    result = QualityEvaluator().evaluate("code", "agent_1", "backend", {"code_quality": 1.0})
    assert result.details["domain"] == "backend"
    assert result.details["solution_length"] == 4


def test_custom_threshold() -> None:
    evaluator = QualityEvaluator(quality_threshold=0.1)
    result = evaluator.evaluate("print('hi')", "agent_1", "backend", {"code_quality": 1.0})
    assert result.passed is True
