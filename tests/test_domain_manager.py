"""Tests for competency domain loading and validation."""

from pathlib import Path

import pytest

from openorchestra.core.domain_manager import DomainConfig, DomainManager


class FakeDetector:
    def __init__(self, available: set[str] | None = None) -> None:
        self.available = available or set()

    def detect_installed_skills(self):
        class Info:
            def __init__(self, name: str) -> None:
                self.name = name
                self.available = True

        return {name: Info(name) for name in self.available}


def test_loads_all_nine_default_domains() -> None:
    manager = DomainManager()
    ids = {domain.id for domain in manager.list_domains()}

    assert len(ids) == 9
    assert ids == {
        "backend",
        "frontend_ui_ux",
        "devops_cloud",
        "security",
        "data_ml",
        "qa_testing",
        "architecture",
        "agent_orchestration",
        "code_refinement",
    }


def test_evaluation_criteria_are_normalised_to_weight_dict() -> None:
    manager = DomainManager()

    for domain in manager.list_domains():
        assert isinstance(domain.evaluation_criteria, dict)
        assert domain.evaluation_criteria
        assert all(isinstance(k, str) for k in domain.evaluation_criteria)
        assert all(isinstance(v, float) for v in domain.evaluation_criteria.values())
        assert sum(domain.evaluation_criteria.values()) == pytest.approx(1.0)


def test_get_unknown_domain_returns_none() -> None:
    assert DomainManager().get_domain("nope") is None


def test_custom_domains_file_is_loaded(domains_file: Path) -> None:
    manager = DomainManager(domains_path=str(domains_file))

    domain = manager.get_domain("demo")
    assert isinstance(domain, DomainConfig)
    assert domain.default_agent_count == 2
    assert domain.evaluation_criteria == {"code_quality": 0.6, "test_coverage": 0.4}


def test_legacy_list_criteria_are_accepted(tmp_path: Path) -> None:
    path = tmp_path / "legacy.yaml"
    path.write_text(
        """
domains:
  legacy:
    name: "Legacy"
    description: "Legacy list format"
    required_skills: []
    default_agent_count: 3
    evaluation_criteria:
      - code_quality: 0.5
      - security_standards: 0.5
""",
        encoding="utf-8",
    )

    domain = DomainManager(domains_path=str(path)).get_domain("legacy")
    assert domain is not None
    assert domain.evaluation_criteria == {"code_quality": 0.5, "security_standards": 0.5}

    # Legacy weights must be normalised to sum to 1.
    path.write_text(
        """
domains:
  legacy:
    name: "Legacy"
    evaluation_criteria:
      - code_quality: 1
      - security_standards: 1
""",
        encoding="utf-8",
    )
    domain = DomainManager(domains_path=str(path)).get_domain("legacy")
    assert domain is not None
    assert sum(domain.evaluation_criteria.values()) == pytest.approx(1.0)


def test_invalid_criteria_are_ignored_and_positive_weights_normalised(tmp_path: Path) -> None:
    path = tmp_path / "invalid_criteria.yaml"
    path.write_text(
        """
domains:
  messy:
    name: "Messy"
    evaluation_criteria:
      good: 2
      zero: 0
      negative: -3
      text: "not-a-number"
  legacy_mixed:
    name: "Legacy mixed"
    evaluation_criteria:
      - code_quality: 1
      - broken
      - security: 1
  extra:
    name: "Unsupported"
    evaluation_criteria: "not-a-mapping"
""",
        encoding="utf-8",
    )

    manager = DomainManager(domains_path=str(path))
    messy = manager.get_domain("messy")
    assert messy is not None
    assert messy.evaluation_criteria == {"good": 1.0}

    legacy = manager.get_domain("legacy_mixed")
    assert legacy is not None
    assert legacy.evaluation_criteria == {"code_quality": 0.5, "security": 0.5}

    extra = manager.get_domain("extra")
    assert extra is not None
    assert extra.evaluation_criteria == {}


def test_user_domains_are_merged_with_defaults(tmp_path: Path) -> None:
    user_file = tmp_path / "user_domains.yaml"
    user_file.write_text(
        """
domains:
  mobile:
    name: "Mobile"
    description: "Mobile apps"
    required_skills: []
    default_agent_count: 2
    evaluation_criteria:
      mobile_performance: 1.0
""",
        encoding="utf-8",
    )

    manager = DomainManager(user_domains_path=str(user_file))
    assert manager.get_domain("mobile") is not None
    assert manager.get_domain("backend") is not None


def test_default_config_loads_outside_repository(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    manager = DomainManager()
    assert len(manager.list_domains()) == 9


def test_availability_uses_detected_skills() -> None:
    manager = DomainManager(skill_detector=FakeDetector({"clean-code", "system-design"}))
    assert manager.is_domain_available("backend") is True

    manager = DomainManager(skill_detector=FakeDetector())
    assert manager.is_domain_available("backend") is False


def test_available_domains_are_filtered() -> None:
    manager = DomainManager(skill_detector=FakeDetector({"clean-code", "system-design"}))
    available = {d.id for d in manager.get_available_domains()}
    assert "backend" in available
    assert "frontend_ui_ux" not in available


def test_malformed_domain_values_fall_back(tmp_path: Path) -> None:
    path = tmp_path / "malformed.yaml"
    path.write_text(
        """
domains:
  malformed:
    name: "Malformed"
    required_skills: "clean-code"
    default_agent_count: "many"
    evaluation_criteria:
      code_quality: 1
""",
        encoding="utf-8",
    )

    domain = DomainManager(domains_path=str(path)).get_domain("malformed")

    assert domain is not None
    assert domain.default_agent_count == 3
    assert domain.required_skills == ["clean-code"]


def test_invalid_yaml_is_rejected_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("not: [valid", encoding="utf-8")

    manager = DomainManager(domains_path=str(path))
    assert manager.list_domains() == []
