"""Documentation consistency checks."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_local_links_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\((?!https?://)([^)#]+)\)", readme)

    assert links
    for link in links:
        assert (ROOT / link).exists(), f"Broken README link: {link}"


def test_documented_architecture_paths_exist() -> None:
    for path in [
        "src/openorchestra/cli/main.py",
        "src/openorchestra/core/domain_manager.py",
        "src/openorchestra/core/skill_detector.py",
        "src/openorchestra/evaluators/quality_evaluator.py",
        "src/openorchestra/integrations/opencode_adapter.py",
        "src/openorchestra/memory/competition_memory.py",
        "src/openorchestra/configs/default_domains.yaml",
        "src/openorchestra/configs/default_competition_config.yaml",
    ]:
        assert (ROOT / path).exists(), f"Missing documented path: {path}"


def test_pyproject_requires_python_311() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.11"' in pyproject
    assert 'openorchestra = "openorchestra.cli.main:cli"' in pyproject
