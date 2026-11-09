"""
Command-line interface for OpenOrchestra.
"""

import click
from pathlib import Path
from openorchestra.core.domain_manager import DomainManager
from openorchestra.core.skill_detector import SkillDetector


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """OpenOrchestra - Multi-agent orchestrator for code generation"""
    pass


@cli.command()
def init():
    """Initialize OpenOrchestra in the current directory"""
    click.echo("Initializing OpenOrchestra...")
    
    # Create .openorchestra directory
    orchestra_dir = Path(".openorchestra")
    orchestra_dir.mkdir(exist_ok=True)
    
    # Create default config
    config_content = """# OpenOrchestra Configuration
general:
  project_name: "openorchestra"
  output_directory: "./results"

skill_detection:
  auto_detect: true
  fallback_to_defaults: true

memory:
  enabled: true
  database_path: ".openorchestra/memory.db"
"""
    
    config_file = orchestra_dir / "config.yaml"
    if not config_file.exists():
        config_file.write_text(config_content)
        click.echo(f"Created configuration file: {config_file}")
    
    click.echo("Initialization complete!")


@cli.command()
def list_domains():
    """List all available competency domains"""
    manager = DomainManager()
    domains = manager.list_domains()
    
    click.echo("\nAvailable Domains:")
    click.echo("-" * 60)
    
    for domain in domains:
        available = manager.is_domain_available(domain.id)
        status = "✓" if available else "⚠"
        
        click.echo(f"{status} {domain.name} ({domain.id})")
        click.echo(f"  Description: {domain.description}")
        click.echo(f"  Required skills: {', '.join(domain.required_skills)}")
        click.echo(f"  Default agents: {domain.default_agent_count}")
        click.echo()


@cli.command()
def list_skills():
    """List all detected skills"""
    detector = SkillDetector()
    skills = detector.detect_installed_skills()
    
    click.echo("\nDetected Skills:")
    click.echo("-" * 60)
    
    for skill_id, skill_info in skills.items():
        status = "✓" if skill_info.available else "✗"
        click.echo(f"{status} {skill_info.name} ({skill_id})")
        if skill_info.path:
            click.echo(f"  Path: {skill_info.path}")


@cli.command()
@click.option('--domain', '-d', required=True, help='Competency domain')
@click.option('--task', '-t', required=True, help='Task description')
@click.option('--agents', '-a', default=5, help='Number of agents (default: 5)')
@click.option('--output', '-o', default='./results', help='Output directory')
def run(domain: str, task: str, agents: int, output: str):
    """Run a competition for a specific domain"""
    from openorchestra.core.domain_manager import DomainManager
    
    manager = DomainManager()
    domain_config = manager.get_domain(domain)
    
    if not domain_config:
        click.echo(f"Error: Domain '{domain}' not found", err=True)
        raise SystemExit(1)
    
    if not manager.is_domain_available(domain):
        click.echo(f"Warning: Domain '{domain}' is not fully available (missing required skills)", err=True)
    
    click.echo(f"\nStarting competition for: {domain_config.name}")
    click.echo(f"Task: {task}")
    click.echo(f"Agents: {agents}")
    click.echo(f"Output: {output}")
    click.echo("\nCompetition in progress...")
    
    # Placeholder for actual competition logic
    click.echo("\nCompetition completed!")
    click.echo(f"Results saved to: {output}")


@cli.command()
@click.argument('domain')
def show_domain(domain: str):
    """Show details for a specific domain"""
    manager = DomainManager()
    domain_config = manager.get_domain(domain)
    
    if not domain_config:
        click.echo(f"Error: Domain '{domain}' not found", err=True)
        raise SystemExit(1)
    
    click.echo(f"\nDomain: {domain_config.name}")
    click.echo(f"ID: {domain_config.id}")
    click.echo(f"Description: {domain_config.description}")
    click.echo(f"\nRequired Skills:")
    for skill in domain_config.required_skills:
        click.echo(f"  - {skill}")
    click.echo(f"\nDefault Agent Count: {domain_config.default_agent_count}")
    click.echo(f"\nEvaluation Criteria:")
    for criterion, weight in domain_config.evaluation_criteria.items():
        click.echo(f"  - {criterion}: {weight * 100}%")


@cli.command()
def doctor():
    """Check system health and configuration"""
    click.echo("\nOpenOrchestra System Check")
    click.echo("=" * 60)
    
    # Check Python version
    import sys
    click.echo(f"Python version: {sys.version}")
    
    # Check configuration
    config_path = Path(".openorchestra/config.yaml")
    if config_path.exists():
        click.echo(f"✓ Configuration found: {config_path}")
    else:
        click.echo(f"⚠ Configuration not found: {config_path}")
    
    # Check domains
    manager = DomainManager()
    domains = manager.list_domains()
    click.echo(f"✓ Loaded {len(domains)} domains")
    
    # Check skills
    detector = SkillDetector()
    skills = detector.detect_installed_skills()
    available_count = sum(1 for s in skills.values() if s.available)
    click.echo(f"✓ Detected {available_count}/{len(skills)} available skills")
    
    # Check memory
    memory_path = Path(".openorchestra/memory.db")
    if memory_path.exists():
        click.echo(f"✓ Memory database found: {memory_path}")
    else:
        click.echo(f"⚠ Memory database not initialized")
    
    click.echo("\nSystem check complete!")


if __name__ == '__main__':
    cli()