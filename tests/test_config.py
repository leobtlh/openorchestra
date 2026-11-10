"""Tests for project configuration loading."""

from pathlib import Path

from openorchestra.core.competition_orchestrator import CompetitionOrchestrator
from openorchestra.core.config import load_config
from openorchestra.memory.competition_memory import CompetitionMemory


def test_missing_config_returns_empty_mapping(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.yaml") == {}


def test_unusable_config_returns_empty_mapping(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"

    for content in ("not: [valid", "- just\n- a list\n"):
        path.write_text(content, encoding="utf-8")
        assert load_config(path) == {}


def test_orchestrator_applies_project_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    database_path = tmp_path / "configured-memory.db"
    config_path.write_text(
        f"""
memory:
  database_path: "{database_path}"
optimization:
  max_agents: 2
  min_improvement_threshold: 0.1
  budget_limit_tokens: 12345
  budget_limit_usd: 12.5
evaluation:
  quality_threshold: 0.6
agents:
  timeout_per_agent: 45
defaults:
  default_agent_count: 2
general:
  output_directory: "./configured-results"
""",
        encoding="utf-8",
    )

    orchestrator = CompetitionOrchestrator(config_path=str(config_path))

    assert orchestrator.optimizer.max_agents == 2
    assert orchestrator.optimizer.min_improvement_threshold == 0.1
    assert orchestrator.evaluator.quality_threshold == 0.6
    assert orchestrator.memory.db_path == str(database_path)
    assert orchestrator.default_agent_count == 2
    assert orchestrator.default_timeout == 45
    assert orchestrator.default_budget_tokens == 12345
    assert orchestrator.default_budget_usd == 12.5
    assert orchestrator.output_directory == "./configured-results"


def test_explicit_components_override_project_config(
    memory: CompetitionMemory, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("memory:\n  database_path: ignored.db\n", encoding="utf-8")

    orchestrator = CompetitionOrchestrator(config_path=str(config_path), memory=memory)

    assert orchestrator.memory is memory
