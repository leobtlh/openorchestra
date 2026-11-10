"""Shared pytest fixtures for the OpenOrchestra test suite."""

from pathlib import Path

import pytest

from openorchestra.memory.competition_memory import CompetitionMemory


@pytest.fixture
def memory(tmp_path: Path) -> CompetitionMemory:
    """A memory instance backed by a throw-away SQLite database."""
    return CompetitionMemory(db_path=str(tmp_path / "memory.db"))


@pytest.fixture
def domains_file(tmp_path: Path) -> Path:
    """A minimal valid domain configuration file."""
    path = tmp_path / "domains.yaml"
    path.write_text(
        """
domains:
  demo:
    name: "Demo"
    description: "Demo domain"
    required_skills: ["clean-code"]
    default_agent_count: 2
    evaluation_criteria:
      code_quality: 0.6
      test_coverage: 0.4
""",
        encoding="utf-8",
    )
    return path
