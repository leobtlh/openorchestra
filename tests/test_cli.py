"""CLI integration tests."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from openorchestra.cli.main import cli


def invoke(args: list[str], cwd: Path):
    return CliRunner().invoke(cli, args, catch_exceptions=False)


def run_competition(
    tmp_path: Path,
    *extra: str,
    domain: str = "backend",
    task: str = "Create an endpoint",
    agents: int | None = None,
):
    args = ["run", "--domain", domain, "--task", task, "--output", str(tmp_path / "results")]
    if agents is not None:
        args += ["--agents", str(agents)]
    args += list(extra)
    return invoke(args, tmp_path)


def read_result(tmp_path: Path) -> dict:
    result_files = list((tmp_path / "results").glob("competition_*.json"))
    assert len(result_files) == 1
    return json.loads(result_files[0].read_text(encoding="utf-8"))


def test_version() -> None:
    result = invoke(["--version"], Path.cwd())
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_init_creates_configuration(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".openorchestra" / "config.yaml"

    first = invoke(["init"], tmp_path)
    assert first.exit_code == 0
    assert config.is_file()

    config.write_text("custom: true\n", encoding="utf-8")
    second = invoke(["init"], tmp_path)
    assert second.exit_code == 0
    assert config.read_text(encoding="utf-8") == "custom: true\n"


def test_list_domains(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(["list-domains"], tmp_path)

    assert result.exit_code == 0
    assert "Backend Development" in result.output
    assert "(backend)" in result.output
    assert result.output.count("Description:") == 9


@pytest.mark.parametrize(
    ("domain", "exit_code", "expected"),
    [("backend", 0, "Backend Development"), ("nope", 1, "not found")],
)
def test_show_domain(
    tmp_path: Path, monkeypatch, domain: str, exit_code: int, expected: str
) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(["show-domain", domain], tmp_path)

    assert result.exit_code == exit_code
    assert expected in result.output
    if exit_code == 0:
        assert "code_quality" in result.output
        assert "30.0%" in result.output


@pytest.mark.parametrize(
    ("args", "expected"),
    [(["list-skills"], "clean-code"), (["doctor"], "Loaded 9 domains")],
)
def test_diagnostic_commands(tmp_path: Path, monkeypatch, args: list[str], expected: str) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(args, tmp_path)

    assert result.exit_code == 0
    assert expected in result.output


@pytest.mark.parametrize(
    ("extra", "winner_expected"),
    [
        (("--dry-run", "--simulate"), False),
        (("--simulate",), True),
    ],
)
def test_run_writes_result(
    tmp_path: Path, monkeypatch, extra: tuple[str, ...], winner_expected: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_competition(tmp_path, *extra, agents=2)

    assert result.exit_code == 0
    data = read_result(tmp_path)
    assert len(data["agent_results"]) == 2
    if winner_expected:
        assert "Competition completed" in result.output
        assert data["winner"] in {"agent_1", "agent_2"}
    else:
        assert data["winner"] is None


def test_run_uses_config_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init"], tmp_path)
    (tmp_path / ".openorchestra" / "config.yaml").write_text(
        """
general:
  output_directory: "./configured-results"
defaults:
  default_agent_count: 2
agents:
  timeout_per_agent: 45
""",
        encoding="utf-8",
    )

    result = invoke(
        ["run", "--domain", "backend", "--task", "Configured task", "--simulate"],
        tmp_path,
    )

    assert result.exit_code == 0
    result_files = list((tmp_path / "configured-results").glob("competition_*.json"))
    assert len(result_files) == 1
    data = json.loads(result_files[0].read_text(encoding="utf-8"))
    assert len(data["agent_results"]) == 2


def test_run_with_optimizer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_competition(
        tmp_path, "--optimize", "--complexity", "0.9", "--simulate", task="Complex task"
    )

    assert result.exit_code == 0
    assert len(read_result(tmp_path)["agent_results"]) == 4


@pytest.mark.parametrize(
    ("domain", "agents", "expected"),
    [("nope", None, "not found"), ("backend", 9, "between 1 and 5")],
)
def test_run_rejects_invalid_input(
    tmp_path: Path, monkeypatch, domain: str, agents: int | None, expected: str
) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_competition(tmp_path, "--simulate", domain=domain, agents=agents)

    assert result.exit_code == 1
    assert expected in result.output


def test_create_domain(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(
        [
            "create-domain",
            "--name",
            "Mobile Development",
            "--description",
            "Mobile apps",
            "--skills",
            "react-native,swift",
            "--criteria",
            "mobile_performance:0.6,app_store_compliance:0.4",
        ],
        tmp_path,
    )

    assert result.exit_code == 0
    config = tmp_path / ".openorchestra" / "domains.yaml"
    assert config.is_file()

    listing = invoke(["list-domains"], tmp_path)
    assert "Mobile Development" in listing.output
    assert "(mobile_development)" in listing.output


def test_create_domain_reports_invalid_existing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / ".openorchestra" / "domains.yaml"
    config_path.parent.mkdir()
    config_path.write_text("not: [valid", encoding="utf-8")

    result = invoke(
        ["create-domain", "--name", "Mobile", "--description", "apps"],
        tmp_path,
    )

    assert result.exit_code == 1
    assert "domains.yaml" in result.output
    assert "Could not read" in result.output


@pytest.mark.parametrize("criteria", [":0.5", "quality:0", "quality:-1", "quality:nan"])
def test_create_domain_rejects_invalid_criteria(tmp_path: Path, monkeypatch, criteria: str) -> None:
    monkeypatch.chdir(tmp_path)

    result = invoke(
        ["create-domain", "--name", "Mobile", "--criteria", criteria],
        tmp_path,
    )

    assert result.exit_code == 1
    assert "Invalid criterion" in result.output


def test_doctor_reports_configured_memory_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".openorchestra" / "config.yaml"
    config.parent.mkdir()
    config.write_text("memory:\n  database_path: custom/memory.db\n", encoding="utf-8")
    memory_dir = tmp_path / "custom"
    memory_dir.mkdir()
    (memory_dir / "memory.db").touch()

    result = invoke(["doctor"], tmp_path)

    assert result.exit_code == 0
    assert "custom/memory.db" in result.output
    assert "Memory database found" in result.output
