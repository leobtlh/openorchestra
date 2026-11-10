# Developer Guide

This guide covers the package layout, development commands, and the main
extension points.

## Package layout

All importable code lives under `src/openorchestra/`:

```
src/openorchestra/
├── cli/main.py               # Click entry point
├── configs/                  # Packaged YAML configuration
├── core/                     # Orchestration, learning, optimization
├── evaluators/               # Solution scoring
├── integrations/             # OpenCode, AutoDev, Agent Arena adapters
├── memory/                   # Persistent SQLite memory
├── domains/                  # Domain package namespace
├── skills/                   # Skill package namespace
└── utils/                    # Shared helpers
```

`configs/*.yaml` is included as package data, so an installed wheel works
without the repository checkout. `DomainManager` reads the packaged file with
`importlib.resources` and then merges `.openorchestra/domains.yaml` from the
current project.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Required checks

Run these before opening a pull request:

```bash
pytest -q
ruff check src tests
black --check src tests
mypy src
```

The test suite uses simulated agents by default; it does not call a model
provider or the `opencode` binary.

## Project configuration

`load_config()` reads `.openorchestra/config.yaml` (or an explicit path) and
returns a mapping. `CompetitionOrchestrator` uses it to configure memory,
evaluation threshold, optimizer limits, default agent count, default timeout,
and the output directory.

```python
from openorchestra.core.config import load_config

settings = load_config(".openorchestra/config.yaml")
```

Invalid or missing files are treated as an empty configuration, so defaults
remain usable in CI.

## Core workflow

`CompetitionOrchestrator.run_competition()` performs:

1. Domain lookup and configuration validation.
2. Optional agent-count optimisation.
3. Task preparation with learned patterns from memory.
4. Agent execution through OpenCode or AutoDev.
5. Weighted evaluation with `QualityEvaluator`.
6. Winner selection.
7. Optional memory and hierarchical learning updates.

`CompetitionConfig` controls the run. Useful fields:

| Field | Meaning |
|-------|---------|
| `domain` | Built-in or custom domain ID |
| `task_description` | Task sent to every agent |
| `agent_count` | Number of agents (1–5) |
| `use_opencode` / `use_autodev` | Execution backend |
| `simulate` | `True` forces deterministic simulation, `None` auto-detects |
| `optimize` | Let `AgentOptimizer` choose the agent count |
| `record_memory` | Persist patterns and the competition outcome |
| `dry_run` | Validate without executing agents |

```python
import asyncio

from openorchestra.core.competition_orchestrator import (
    CompetitionConfig,
    CompetitionOrchestrator,
)

result = asyncio.run(
    CompetitionOrchestrator().run_competition(
        CompetitionConfig(
            domain="backend",
            task_description="Create a safe user endpoint",
            agent_count=3,
            simulate=True,
        )
    )
)
print(result.winner, result.total_score)
```

## Adding a domain

The simplest route is the CLI:

```bash
openorchestra create-domain \
  --name "Mobile Development" \
  --skills "swift,kotlin" \
  --criteria "mobile_performance:0.5,app_store_compliance:0.5"
```

For a built-in domain, add an entry to
`src/openorchestra/configs/default_domains.yaml`. Weights are normalised, so
they do not have to sum to exactly `1.0` in the file, although keeping them
normalised makes the configuration easier to read.

See [DOMAINS_REFERENCE.md](DOMAINS_REFERENCE.md) for the full built-in list.

## Adding a custom skill

`SkillDetector` discovers a skill when one of its search paths contains either
`<skill-id>/` or `<skill-id>.md`:

- `~/.config/opencode/skills`
- `~/.opencode/skills`
- `./skills`

Core skills are always considered available. Additional skills can be declared
in `.openorchestra/config.yaml`:

```yaml
custom_skills:
  - id: mobile-development
    name: Mobile Development
    version: "1.0"
    domains: [mobile_development]
    available: true
    path: ./skills/mobile-development
```

```python
from openorchestra.core.skill_detector import SkillDetector

detector = SkillDetector()
print(detector.detect_installed_skills())
```

## Evaluation

`QualityEvaluator` uses deterministic static heuristics so simulated and live
runs can be compared consistently. It scores the requested domain criteria by
looking for signals such as error handling, tests, type hints, documentation,
security practices, and placeholder/TODO code.

```python
from openorchestra.evaluators.quality_evaluator import QualityEvaluator

result = QualityEvaluator().evaluate(
    solution="def add(a: int, b: int) -> int:\n    return a + b\n",
    agent_id="agent_1",
    domain="backend",
    criteria={"code_quality": 0.6, "maintainability": 0.4},
)
print(result.total_score, result.passed)
```

## Memory

```python
from openorchestra.memory import CompetitionMemory

memory = CompetitionMemory(db_path=".openorchestra/memory.db")
memory.record_pattern(
    domain="backend",
    pattern_type="security",
    description="SQL injection pattern",
    solution="Use parameterized queries",
    confidence=0.9,
)
print(memory.get_context_knowledge("backend"))
```

Writes invalidate the cached context for that domain. Use
`cleanup_expired_patterns(max_age_days=30)` for retention management.

## Agent optimisation

`AgentOptimizer` implements the saturation curve documented in the README:

```python
from openorchestra.core.optimizer import AgentOptimizer

optimizer = AgentOptimizer(max_agents=4)
count = optimizer.calculate_optimal_agent_count(
    task_complexity=0.7,
    budget_tokens=20000,
    budget_usd=20.0,
)
```

The default maximum is 4, the hard cap is 5, and the minimum is 1.
