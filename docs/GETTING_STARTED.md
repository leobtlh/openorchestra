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

| Domain | Description | Default Skills |
|--------|-------------|----------------|
| backend | Backend development, security, databases | clean-code |
| frontend_ui_ux | Frontend & UI/UX design | ui-ux-pro-max |
| devops_cloud | DevOps & cloud infrastructure | - |
| security | Application security | secure-coding |
| data_ml | Data engineering & ML | data-engineering |
| qa_testing | Quality assurance & testing | test-driven-development |
| architecture | System architecture | system-design |
| agent_orchestration | Multi-agent coordination | agentic-delivery |
| code_refinement | Code quality improvement | clean-code |

## Configuration

Edit `.openorchestra/config.yaml` to customize:

```yaml
evaluation:
  timeout_seconds: 300
  quality_threshold: 0.7

agents:
  model_selection: "best_fit"
  max_turns_per_agent: 10
```

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