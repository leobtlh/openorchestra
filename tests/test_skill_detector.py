"""Tests for skill detection."""

from pathlib import Path

from openorchestra.core.skill_detector import SkillDetector, SkillInfo


def test_detects_default_skills_without_crashing(tmp_path: Path) -> None:
    detector = SkillDetector(search_paths=[tmp_path])
    skills = detector.detect_installed_skills()

    assert isinstance(skills["clean-code"], SkillInfo)
    assert skills["clean-code"].available is True
    assert skills["ui-ux-pro-max"].available is False


def test_detects_skill_from_search_path(tmp_path: Path) -> None:
    skill_dir = tmp_path / "ui-ux-pro-max"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# skill", encoding="utf-8")

    detector = SkillDetector(search_paths=[tmp_path])
    skills = detector.detect_installed_skills()

    assert skills["ui-ux-pro-max"].available is True
    assert skills["ui-ux-pro-max"].path == str(skill_dir)


def test_detects_flat_skill_markdown_file(tmp_path: Path) -> None:
    (tmp_path / "custom-skill.md").write_text("# skill", encoding="utf-8")

    detector = SkillDetector(
        search_paths=[tmp_path],
        default_skills={"custom-skill": "Custom Skill"},
    )
    skills = detector.detect_installed_skills()

    assert skills["custom-skill"].available is True


def test_custom_skills_are_loaded_from_config(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
custom_skills:
  - id: "my-skill"
    name: "My Skill"
    version: "1.2"
    domains: ["backend"]
    path: "/tmp/my-skill"
""",
        encoding="utf-8",
    )

    detector = SkillDetector(config_path=str(config), search_paths=[tmp_path])
    skills = detector.detect_installed_skills()

    assert skills["my-skill"].name == "My Skill"
    assert skills["my-skill"].version == "1.2"
    assert skills["my-skill"].domains == ["backend"]
    assert skills["my-skill"].available is True


def test_corrupt_custom_config_is_ignored(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("custom_skills: [", encoding="utf-8")

    detector = SkillDetector(config_path=str(config), search_paths=[tmp_path])
    assert "clean-code" in detector.detect_installed_skills()


def test_required_skills_for_known_domain() -> None:
    detector = SkillDetector(search_paths=[])
    assert detector.get_required_skills("backend") == ["clean-code", "system-design"]
    assert detector.get_required_skills("unknown") == []


def test_available_domains_helper_does_not_crash() -> None:
    detector = SkillDetector(search_paths=[])
    available = detector.get_available_domains()
    assert isinstance(available, list)
    assert "backend" in available
