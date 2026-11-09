"""Packaging and public API contract tests."""

from importlib import metadata, resources

import click
from click.testing import CliRunner

import openorchestra


def test_package_import_exposes_version() -> None:
    assert openorchestra.__version__ == "0.1.0"


def test_distribution_is_installed_as_openorchestra() -> None:
    dist = metadata.distribution("openorchestra")
    assert dist.version == "0.1.0"

    top_level = (dist.read_text("top_level.txt") or "").split()
    assert top_level == ["openorchestra"]


def test_console_script_points_to_cli() -> None:
    entry_points = metadata.entry_points(group="console_scripts")
    script = next(ep for ep in entry_points if ep.name == "openorchestra")
    assert script.value == "openorchestra.cli.main:cli"


def test_default_domains_file_is_packaged() -> None:
    config = resources.files("openorchestra").joinpath("configs/default_domains.yaml")
    assert config.is_file()
    assert "domains:" in config.read_text(encoding="utf-8")


def test_cli_help_runs() -> None:
    from openorchestra.cli.main import cli

    assert isinstance(cli, click.Group)
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "OpenOrchestra" in result.output
