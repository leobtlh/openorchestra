# OpenOrchestra

OpenOrchestra is an agnostic multi-agent orchestrator for code generation and evaluation. It enables competitions among multiple specialized agents to produce higher-quality code through automatic evaluation based on objective criteria and persistent memory.

## Vision

Code produced by a single AI agent has inherent limitations. By pitting multiple competent agents against each other with objective criteria, we achieve improved code quality through natural selection. OpenOrchestra automates this process.

## Features

- **Automatic skill detection**: Detects available skills in your OpenCode environment
- **Predefined competency domains**: 9 domains covering main software engineering competencies
- **Plugin architecture**: Easily add new domains and skills
- **Persistent memory**: Learns from past errors to improve future iterations
- **Automatic evaluation**: Objective criteria for solution comparison
- **FreeLLMAPI/OpenRouter compatible**: Works with all your model providers

## Installation

```bash
cd /path/to/your/project
pip install -e .
```

## Usage

### Initialization

```bash
# Create default configuration
openorchestra init

# List available domains
openorchestra list-domains
```

### Running a Competition

```bash
# UI/UX competition with 5 agents
openorchestra run \
  --domain frontend_ui_ux \
  --task "Create a design system for a SaaS application" \
  --agents 5 \
  --output ./results/
```

### Configuration

```yaml
# .openorchestra/competition_config.yaml
domains:
  frontend_ui_ux:
    name: "Frontend Development & UI/UX"
    required_skills:
      - "ui-ux-pro-max"
      - "design-taste-frontend"
    default_agent_count: 5
    evaluation_criteria:
      design_system_compliance: 0.4
      accessibility_standards: 0.3
      responsive_behavior: 0.3
```

## Competency Domains

OpenOrchestra supports 9 primary domains based on IEEE/SWECOM standards:

1. **Backend** - Backend development, security, databases
2. **Frontend/UI-UX** - Interfaces, UX, design systems, accessibility
3. **DevOps/Cloud** - Infrastructure, CI/CD, orchestration, monitoring
4. **Security** - Application security, pentesting, compliance
5. **Data/ML** - Data pipelines, machine learning, data quality
6. **QA/Testing** - Automated testing, quality, coverage
7. **Architecture** - System design, scalability, patterns
8. **Agent Orchestration** - Multi-agent coordination, tournaments
9. **Code Refinement** - Self-refinement, quality, optimization

## Architecture

```
openorchestra/
├── src/
│   └── openorchestra/          # Installable package
│       ├── __init__.py
│       ├── py.typed            # PEP 561 marker
│       ├── cli/                # Command-line interface
│       │   └── main.py         # CLI entry point
│       ├── configs/            # Packaged YAML configuration
│       │   ├── default_domains.yaml
│       │   └── default_competition_config.yaml
│       ├── core/               # Orchestration and learning
│       │   ├── competition_orchestrator.py
│       │   ├── config.py       # Project configuration loader
│       │   ├── domain_manager.py
│       │   ├── skill_detector.py
│       │   ├── agent_interface.py
│       │   ├── agent_pool.py
│       │   ├── optimizer.py
│       │   ├── lru_cache.py
│       │   ├── pattern_signature.py
│       │   ├── pattern_cluster.py
│       │   ├── context_compressor.py
│       │   └── hierarchical_learner.py
│       ├── domains/            # Competency domain package
│       ├── evaluators/         # Evaluation system
│       │   └── quality_evaluator.py
│       ├── integrations/       # External tool adapters
│       │   ├── opencode_adapter.py
│       │   ├── autodev_adapter.py
│       │   ├── agent_arena_bridge.py
│       │   └── process.py      # External command probing
│       ├── memory/             # Persistent learning
│       │   └── competition_memory.py
│       ├── skills/             # Skill definitions
│       └── utils/              # Utility functions
├── docs/
│   ├── ARCHITECTURE.md         # Detailed architecture
│   ├── DOMAINS_REFERENCE.md    # Domain and criteria reference
│   ├── DEVELOPMENT.md          # Developer extension guide
│   ├── GETTING_STARTED.md      # Quick start guide
│   └── MEMORY_OPTIMIZATION.md  # Memory design notes
├── examples/
│   └── basic_competition.py
├── tests/
├── README.md
├── CONTRIBUTING.md
└── pyproject.toml
```

## Persistent Memory

The system maintains learned lessons in a local database:

```python
from openorchestra.memory import CompetitionMemory

memory = CompetitionMemory()

# After each competition
memory.record_competition_outcome(
    domain="frontend_ui_ux",
    agent_count=3,
    winner_agent="ux_agent_2",
    best_score=0.85,
    total_cost_usd=0.12,
)

# Store a reusable technical pattern
memory.record_pattern(
    domain="frontend_ui_ux",
    pattern_type="accessibility",
    description="Missing focus styles on interactive elements",
    solution="Add :focus-visible styles and keyboard navigation",
    confidence=0.9,
)

# Use this knowledge for future competitions
improved_prompt = memory.get_context_knowledge(domain="frontend_ui_ux")
```

## Automatic Evaluation

Each solution is evaluated according to predefined criteria:

- Code quality (lint, cyclomatic complexity)
- Tests (passing, coverage)
- Performance (execution time)
- Compliance (standards, style guides)
- Accessibility (WCAG)
- Security (vulnerabilities)

## Extension

Adding a new domain:

```bash
openorchestra create-domain \
  --name "mobile_development" \
  --skills "react-native,swift,kotlin" \
  --criteria "mobile_performance,app_store_compliance,battery_optimization"
```

Adding a new skill:

```yaml
# skills/mobile_development.yaml
name: "Mobile Development Expertise"
compatible_agents: ["mobile_agent_1", "mobile_agent_2"]
evaluation_metrics:
  - mobile_performance_index: 0.4
  - cross_platform_compatibility: 0.3
  - app_store_guidelines: 0.3
```

## Agent Optimization

OpenOrchestra uses research-backed optimization to determine the optimal number of agents. Based on Hovsky et al. (2023) "Evaluating the Trade-offs of Multi-Agent Competition in Large Language Model Workflows", the system implements a **saturation curve model**:

```
Performance Gain(%) = 100 / (1 + e^(-k*(n-1)))
```

Where `k = 0.7` (saturation factor) and `n` is the agent count.

### Key Findings from Hovsky et al.

| Agents | Performance Gain | Cost Increase | Gain per Cost Unit |
|--------|------------------|---------------|--------------------|
| 1 | 50.0% | 1x | 0.500 |
| 2 | 66.8% | 2x | 0.334 |
| 3 | 80.2% | 3x | 0.267 |
| 4 | 89.1% | 4x | 0.223 |
| 5 | 94.3% | 5x | 0.189 |

**Optimal Range: 2-4 agents** (sweet spot for cost/quality trade-off)

The values above come directly from the saturation curve with `k = 0.7`; the
optimizer exposes the same calculation as `estimate_performance_gain(n)`.

### Dynamic Agent Allocation

The optimizer automatically adjusts agent count based on:

1. **Task Complexity**: Simple tasks (0.3) → 2 agents, Complex (0.7+) → 4 agents
2. **Budget Constraints**: Token/USD limits prevent overspending
3. **Convergence Detection**: Stops when quality improvement < 3%
4. **Historical Learning**: Remembers what worked for similar tasks

### Usage

```bash
# Auto-optimize agent count based on task
openorchestra run \
  --domain frontend_ui_ux \
  --task "Create a login page" \
  --optimize  # Automatically uses 2-3 agents
```

```python
from openorchestra.core import AgentOptimizer

optimizer = AgentOptimizer()
optimal_count = optimizer.calculate_optimal_agent_count(
    task_complexity=0.6,
    budget_tokens=20000,
    budget_usd=20.0
)
# Returns: 3 (optimal for this scenario)
```

### Default Configuration

```yaml
# .openorchestra/config.yaml
optimization:
  max_agents: 4              # Never exceed 4 by default
  min_improvement_threshold: 0.03  # Stop if gain < 3%
  budget_limit_tokens: 50000
  budget_limit_usd: 50.0
```

## Integrations

- **OpenCode**: Native skill and agent detection
- **AutoDev**: Adapter for automatic tournaments
- **Agent Arena**: Bridge for external competitions
- **FreeLLMAPI**: Support for model providers without API keys

## Documentation

- [Getting started guide](docs/GETTING_STARTED.md)
- [Detailed architecture](docs/ARCHITECTURE.md)
- [Developer extension guide](docs/DEVELOPMENT.md)
- [Domain reference](docs/DOMAINS_REFERENCE.md)
- [Memory optimization](docs/MEMORY_OPTIMIZATION.md)

## License

GPL-3.0

## Contributing

Contributors are welcome. Please consult CONTRIBUTING.md for contribution details.