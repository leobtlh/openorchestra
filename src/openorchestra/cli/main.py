"""
Command-line interface for OpenOrchestra.
"""

import asyncio
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import click
import yaml

from openorchestra import __version__
from openorchestra.core.competition_orchestrator import (
    CompetitionConfig,
    CompetitionOrchestrator,
)
from openorchestra.core.config import load_config
from openorchestra.core.domain_manager import DomainManager
from openorchestra.core.skill_detector import SkillDetector

CONFIG_TEMPLATE = """# OpenOrchestra Configuration
general:
  project_name: "openorchestra"
  output_directory: "./results"

skill_detection:
  auto_detect: true
  fallback_to_defaults: true

memory:
  enabled: true
  database_path: ".openorchestra/memory.db"

evaluation:
  quality_threshold: 0.7

agents:
  timeout_per_agent: 300

defaults:
  default_agent_count: 3

optimization:
  max_agents: 4
  min_improvement_threshold: 0.03
  budget_limit_tokens: 50000
  budget_limit_usd: 50.0
"""


def _fail(message: str) -> NoReturn:
    click.echo(message, err=True)
    raise SystemExit(1)


def _normalise_identifier(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "custom_domain"


def _resolve_run_defaults(
    orchestrator: CompetitionOrchestrator,
    agents: int | None,
    output: str | None,
    timeout_per_agent: int | None,
    budget_tokens: int | None,
    budget_usd: float | None,
) -> tuple[int, str, int, int, float]:
    """Resolve CLI options against project configuration defaults."""
    return (
        orchestrator.default_agent_count if agents is None else agents,
        output or orchestrator.output_directory,
        orchestrator.default_timeout if timeout_per_agent is None else timeout_per_agent,
        orchestrator.default_budget_tokens if budget_tokens is None else budget_tokens,
        orchestrator.default_budget_usd if budget_usd is None else budget_usd,
    )


def _parse_criterion(chunk: str) -> tuple[str, float] | None:
    """Parse one ``name[:weight]`` criterion, returning None for blanks."""
    chunk = chunk.strip()
    if not chunk:
        return None

    name, separator, weight = chunk.partition(":")
    name = name.strip()
    if not name:
        _fail(f"Invalid criterion name: {chunk}")
    if not separator:
        return name, 1.0

    try:
        value = float(weight)
    except ValueError:
        _fail(f"Invalid criterion weight: {chunk}")
    if not math.isfinite(value) or value <= 0:
        _fail(f"Invalid criterion weight: {chunk}")
    return name, value


def _parse_criteria(raw: str) -> dict[str, float]:
    criteria: dict[str, float] = {}
    for chunk in raw.split(","):
        parsed = _parse_criterion(chunk)
        if parsed is not None:
            criteria[parsed[0]] = parsed[1]

    if not criteria:
        _fail("At least one evaluation criterion is required")
    return criteria


@click.group()
@click.version_option(version=__version__, prog_name="openorchestra")
def cli() -> None:
    """OpenOrchestra - Multi-agent orchestrator for code generation."""


@cli.command()
def init() -> None:
    """Initialize OpenOrchestra in the current directory."""
    click.echo("Initializing OpenOrchestra...")

    orchestra_dir = Path(".openorchestra")
    orchestra_dir.mkdir(parents=True, exist_ok=True)

    config_file = orchestra_dir / "config.yaml"
    if config_file.exists():
        click.echo(f"Configuration already exists: {config_file}")
    else:
        config_file.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        click.echo(f"Created configuration file: {config_file}")

    click.echo("Initialization complete!")


@cli.command()
def list_domains() -> None:
    """List all available competency domains."""
    manager = DomainManager()
    domains = manager.list_domains()

    click.echo("\nAvailable Domains:")
    click.echo("-" * 60)
    for domain in domains:
        status = "OK" if manager.is_domain_available(domain.id) else "MISSING"
        click.echo(f"[{status}] {domain.name} ({domain.id})")
        click.echo(f"  Description: {domain.description}")
        click.echo(f"  Required skills: {', '.join(domain.required_skills)}")
        click.echo(f"  Default agents: {domain.default_agent_count}")
        click.echo()


@cli.command()
def list_skills() -> None:
    """List all detected skills."""
    skills = SkillDetector().detect_installed_skills()

    click.echo("\nDetected Skills:")
    click.echo("-" * 60)
    for skill_id, skill_info in skills.items():
        status = "OK" if skill_info.available else "MISSING"
        click.echo(f"[{status}] {skill_info.name} ({skill_id})")
        if skill_info.path:
            click.echo(f"  Path: {skill_info.path}")


@cli.command()
@click.option("--domain", "-d", required=True, help="Competency domain")
@click.option("--task", "-t", required=True, help="Task description")
@click.option("--agents", "-a", default=None, type=int, help="Number of agents (1-5)")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--optimize", is_flag=True, help="Automatically choose the agent count")
@click.option("--complexity", default=0.5, type=float, help="Task complexity (0-1)")
@click.option("--timeout", "timeout_per_agent", default=None, type=int, help="Timeout per agent")
@click.option("--budget-tokens", type=int, default=None, help="Token budget")
@click.option("--budget-usd", type=float, default=None, help="USD budget")
@click.option("--dry-run", is_flag=True, help="Validate without executing agents")
@click.option("--simulate/--live", default=None, help="Force simulation or live execution")
def run(
    domain: str,
    task: str,
    agents: int | None,
    output: str | None,
    optimize: bool,
    complexity: float,
    timeout_per_agent: int | None,
    budget_tokens: int | None,
    budget_usd: float | None,
    dry_run: bool,
    simulate: bool | None,
) -> None:
    """Run a competition for a specific domain."""
    manager = DomainManager()
    domain_config = manager.get_domain(domain)

    if domain_config is None:
        _fail(f"Error: Domain '{domain}' not found")

    orchestrator = CompetitionOrchestrator()
    (
        agent_count,
        output_directory,
        timeout,
        budget_tokens,
        budget_usd,
    ) = _resolve_run_defaults(
        orchestrator,
        agents,
        output,
        timeout_per_agent,
        budget_tokens,
        budget_usd,
    )

    if not 1 <= agent_count <= 5:
        _fail("Error: --agents must be between 1 and 5")

    click.echo(f"\nStarting competition for: {domain_config.name}")
    click.echo(f"Task: {task}")
    click.echo(f"Agents: {'auto' if optimize else agent_count}")
    click.echo(f"Output: {output_directory}\n")

    config = CompetitionConfig(
        domain=domain,
        task_description=task,
        agent_count=agent_count,
        timeout_per_agent=timeout,
        optimize=optimize,
        task_complexity=complexity,
        budget_tokens=budget_tokens,
        budget_usd=budget_usd,
        dry_run=dry_run,
        simulate=simulate,
    )

    try:
        result = asyncio.run(orchestrator.run_competition(config))
    except ValueError as exc:
        _fail(f"Error: {exc}")

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    result_file = output_path / f"competition_{result.competition_id}.json"
    result_file.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    click.echo("Competition completed!")
    click.echo(f"Winner: {result.winner or 'none'}")
    click.echo(f"Score: {result.total_score:.2f}")
    click.echo(f"Results saved to: {result_file}")


@cli.command()
@click.argument("domain")
def show_domain(domain: str) -> None:
    """Show details for a specific domain."""
    domain_config = DomainManager().get_domain(domain)

    if domain_config is None:
        _fail(f"Error: Domain '{domain}' not found")

    click.echo(f"\nDomain: {domain_config.name}")
    click.echo(f"ID: {domain_config.id}")
    click.echo(f"Description: {domain_config.description}")
    click.echo("\nRequired Skills:")
    for skill in domain_config.required_skills:
        click.echo(f"  - {skill}")
    click.echo(f"\nDefault Agent Count: {domain_config.default_agent_count}")
    click.echo("\nEvaluation Criteria:")
    for criterion, weight in domain_config.evaluation_criteria.items():
        click.echo(f"  - {criterion}: {weight * 100:.1f}%")


@cli.command()
@click.option("--name", required=True, help="Human-readable domain name")
@click.option("--id", "domain_id", default=None, help="Domain identifier")
@click.option("--description", default="", help="Domain description")
@click.option("--skills", default="", help="Comma-separated required skills")
@click.option(
    "--criteria",
    default="code_quality",
    help="Comma-separated criteria, optionally with :weight",
)
def create_domain(
    name: str,
    domain_id: str | None,
    description: str,
    skills: str,
    criteria: str,
) -> None:
    """Create a custom competency domain."""
    domain_id = domain_id or _normalise_identifier(name)
    config_path = Path(".openorchestra/domains.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if config_path.is_file():
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            _fail(f"Could not read {config_path}: {exc}")
        if loaded is not None and not isinstance(loaded, dict):
            _fail(f"Could not read {config_path}: expected a mapping")
        data = loaded or {}
    domains = data.get("domains")
    if not isinstance(domains, dict):
        domains = {}
        data["domains"] = domains

    domains[domain_id] = {
        "name": name,
        "description": description,
        "required_skills": [skill.strip() for skill in skills.split(",") if skill.strip()],
        "default_agent_count": 3,
        "evaluation_criteria": _parse_criteria(criteria),
    }
    config_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    click.echo(f"Created domain '{domain_id}' in {config_path}")


@cli.command()
def doctor() -> None:
    """Check system health and configuration."""
    click.echo("\nOpenOrchestra System Check")
    click.echo("=" * 60)

    click.echo(f"Python version: {sys.version.split()[0]}")

    config_path = Path(".openorchestra/config.yaml")
    if config_path.exists():
        click.echo(f"OK Configuration found: {config_path}")
    else:
        click.echo(f"WARN Configuration not found: {config_path}")

    domains = DomainManager().list_domains()
    click.echo(f"OK Loaded {len(domains)} domains")

    skills = SkillDetector().detect_installed_skills()
    available_count = sum(1 for skill in skills.values() if skill.available)
    click.echo(f"OK Detected {available_count}/{len(skills)} available skills")

    memory_config = load_config(config_path).get("memory", {})
    database_path = ".openorchestra/memory.db"
    if isinstance(memory_config, dict):
        database_path = str(memory_config.get("database_path", database_path))
    memory_path = Path(database_path)
    if memory_path.exists():
        click.echo(f"OK Memory database found: {memory_path}")
    else:
        click.echo("WARN Memory database not initialized")

    try:
        version = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if version.returncode == 0:
            click.echo(f"OK OpenCode available: {version.stdout.strip()}")
        else:
            click.echo("WARN OpenCode executable did not respond")
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        click.echo("WARN OpenCode executable not found (simulation only)")

    click.echo("\nSystem check complete!")


if __name__ == "__main__":
    cli()
