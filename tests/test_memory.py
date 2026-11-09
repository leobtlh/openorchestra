"""Tests for persistent competition memory."""

import sqlite3

from openorchestra.memory.competition_memory import CompetitionMemory


def test_record_pattern_and_lessons(memory: CompetitionMemory) -> None:
    signature = memory.record_pattern(
        domain="backend",
        pattern_type="security",
        description="SQL injection",
        solution="Use parameterized queries",
        confidence=0.9,
    )

    assert len(signature) == 12
    lessons = memory.get_lessons_for_domain("backend")
    assert len(lessons) == 1
    assert lessons[0]["pattern_type"] == "security"
    assert lessons[0]["solution"] == "Use parameterized queries"
    assert lessons[0]["frequency"] == 1


def test_duplicate_pattern_updates_frequency_and_confidence(memory: CompetitionMemory) -> None:
    kwargs = dict(
        domain="backend",
        pattern_type="security",
        description="SQL injection",
        solution="Use parameterized queries",
        confidence=0.6,
    )
    memory.record_pattern(**kwargs)
    memory.record_pattern(**kwargs)

    lessons = memory.get_lessons_for_domain("backend")
    assert len(lessons) == 1
    assert lessons[0]["frequency"] == 2
    assert lessons[0]["confidence"] == 0.6  # latest confidence wins


def test_context_knowledge_returns_empty_string_when_absent(memory: CompetitionMemory) -> None:
    assert memory.get_context_knowledge("unknown") == ""


def test_context_knowledge_is_cached_and_invalidated(memory: CompetitionMemory) -> None:
    assert memory.get_context_knowledge("backend") == ""

    memory.record_pattern(
        domain="backend",
        pattern_type="security",
        description="SQL injection",
        solution="Use parameterized queries",
        confidence=0.9,
    )

    knowledge = memory.get_context_knowledge("backend")
    assert "Use parameterized queries" in knowledge

    memory.record_pattern(
        domain="backend",
        pattern_type="testing",
        description="No tests",
        solution="Add regression tests",
        confidence=0.9,
    )
    assert "Add regression tests" in memory.get_context_knowledge("backend")


def test_low_confidence_patterns_are_not_lessons(memory: CompetitionMemory) -> None:
    memory.record_pattern(
        domain="backend",
        pattern_type="general",
        description="low",
        solution="low confidence",
        confidence=0.2,
    )
    assert memory.get_lessons_for_domain("backend") == []


def test_record_competition_outcome(memory: CompetitionMemory) -> None:
    competition_id = memory.record_competition_outcome(
        domain="backend",
        agent_count=3,
        winner_agent="agent_2",
        best_score=0.84,
        total_cost_usd=0.18,
    )

    assert isinstance(competition_id, int)
    stats = memory.get_stats()
    assert stats["competitions_run"] == 1
    assert stats["patterns_stored"] == 0


def test_update_lesson_success_and_failure(memory: CompetitionMemory) -> None:
    signature = memory.record_pattern(
        domain="backend",
        pattern_type="security",
        description="SQL injection",
        solution="Use parameterized queries",
        confidence=0.6,
    )

    memory.update_lesson_success(signature, "backend", success=True)
    lesson = memory.get_lessons_for_domain("backend")[0]
    assert lesson["success_count"] == 1
    assert lesson["confidence"] > 0.6

    memory.update_lesson_success(signature, "backend", success=False)
    lesson = memory.get_lessons_for_domain("backend")[0]
    assert lesson["confidence"] < 1.0


def test_cleanup_removes_old_patterns(memory: CompetitionMemory) -> None:
    memory.record_pattern(
        domain="backend",
        pattern_type="security",
        description="old",
        solution="old solution",
        confidence=0.9,
    )
    memory.record_pattern(
        domain="backend",
        pattern_type="security",
        description="new",
        solution="new solution",
        confidence=0.9,
    )

    conn = sqlite3.connect(memory.db_path)
    conn.execute("UPDATE patterns SET updated_at = datetime('now', '-60 days') WHERE id = 1")
    conn.commit()
    conn.close()

    assert memory.cleanup_expired_patterns(max_age_days=30) == 1
    assert memory.get_stats()["patterns_stored"] == 1


def test_cache_hit_rate_is_reported(memory: CompetitionMemory) -> None:
    memory.get_context_knowledge("backend")
    memory.get_context_knowledge("backend")
    assert 0.0 <= memory.get_stats()["cache_hit_rate"] <= 1.0
