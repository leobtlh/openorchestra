# Getting Started with OpenOrchestra

## Installation

### Prerequisites
- Python 3.11 or higher
- OpenCode environment with AI coding skills

### Install OpenOrchestra

```bash
# Clone the repository
git clone <repository-url>
cd openorchestra

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize Your Project

```bash
# Run initialization in your project directory
openorchestra init
```

This creates a `.openorchestra/` directory with default configuration.

### 2. Check Available Domains

```bash
# List competency domains
openorchestra list-domains

# List available skills
openorchestra list-skills
```

### 3. Run Your First Competition

```bash
# Run a UI/UX competition
openorchestra run \
  --domain frontend_ui_ux \
  --task "Create a modern landing page for a fintech startup" \
  --agents 5
```

## Understanding Domains

OpenOrchestra supports 9 competency domains based on industry standards:

| Domain | Description | Required Skills |
|--------|-------------|-----------------|
| `backend` | Backend development, security, databases | `clean-code`, `system-design` |
| `frontend_ui_ux` | Frontend & UI/UX design | `ui-ux-pro-max`, `design-taste-frontend` |
| `devops_cloud` | DevOps & cloud infrastructure | `devops-engineer`, `cloud-architecture` |
| `security` | Application security | `secure-coding`, `pentesting` |
| `data_ml` | Data engineering & ML | `data-engineering`, `ml-engineer` |
| `qa_testing` | Quality assurance & testing | `test-driven-development`, `testing-strategies` |
| `architecture` | System architecture | `system-design`, `architectural-patterns` |
| `agent_orchestration` | Multi-agent coordination | `agentic-delivery`, `tournament-management` |
| `code_refinement` | Code quality improvement | `clean-code`, `quality-gates` |

See [DOMAINS_REFERENCE.md](DOMAINS_REFERENCE.md) for the criteria and weights of
each domain.

## Configuration

Edit `.openorchestra/config.yaml` to set project defaults:

```yaml
general:
  output_directory: "./results"

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
```

`openorchestra run` reads these defaults. Explicit CLI flags such as
`--agents`, `--timeout`, `--output`, and `--optimize` take precedence.

## Memory System

The persistent memory learns from past competitions:

```python
from openorchestra import CompetitionMemory

memory = CompetitionMemory()

# Record a learned pattern
memory.record_pattern(
    domain="backend",
    pattern_type="security",
    description="SQL injection vulnerability pattern",
    solution="Use parameterized queries instead of string concatenation"
)
```

## Next Steps

- Read the ARCHITECTURE.md for deeper technical details
- Explore the `examples/` directory for use cases
- Consider contributing your own domains and skills