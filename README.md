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
      - design_system_compliance: 0.4
      - accessibility_standards: 0.3
      - responsive_behavior: 0.3
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
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── skill_detector.py
│   │   └── competition_manager.py
│   ├── domains/
│   │   ├── backend/
│   │   ├── frontend_ui_ux/
│   │   └── ...
│   ├── evaluators/
│   │   └── quality_evaluator.py
│   └── memory/
│       ├── competition_memory.py
│       └── pattern_learner.py
├── skills/
└── configs/
    └── default_domains.yaml
```

## Persistent Memory

The system maintains learned lessons in a local database:

```python
# After each competition
memory.record_outcome(
    domain="frontend_ui_ux",
    agent_id="ux_agent_2",
    solution="code_solution_123",
    score=8.5,
    errors=["accessibility_issue_456"]
)

# Use these knowledge for future competitions
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

## Integrations

- **OpenCode**: Native skill and agent detection
- **AutoDev**: Adapter for automatic tournaments
- **Agent Arena**: Bridge for external competitions
- **FreeLLMAPI**: Support for model providers without API keys

## Documentation

- Getting started guide: docs/GETTING_STARTED.md
- Detailed architecture: docs/ARCHITECTURE.md
- Developer extension guide: docs/DEVELOPMENT.md
- Domain reference: docs/DOMAINS_REFERENCE.md

## License

GPL-3.0

## Contributing

Contributors are welcome. Please consult CONTRIBUTING.md for contribution details.