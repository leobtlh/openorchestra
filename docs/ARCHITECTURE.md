# OpenOrchestra Architecture

## Overview

OpenOrchestra is a multi-agent orchestrator for code generation and evaluation. The system is designed to be agnostic, extensible, and learn from past competitions.

## Core Components

### 1. Domain Manager (`src/core/domain_manager.py`)

Manages competency domains based on IEEE/SWECOM standards:
- 9 predefined domains (backend, frontend, devops, security, etc.)
- Each domain has specific evaluation criteria and required skills
- Dynamically checks skill availability

### 2. Skill Detector (`src/core/skill_detector.py`)

Automatically detects available AI coding skills:
- Scans OpenCode skill directories
- Checks plugin installations
- Fall-back to default skills

### 3. Competition Memory (`src/memory/competition_memory.py`)

Persistent learning system:
- SQLite-based storage
- Records patterns, errors, and solutions
- Provides context for improving future agent performance

### 4. Quality Evaluator (`src/evaluators/quality_evaluator.py`)

Evaluates agent outputs:
- Domain-specific evaluation criteria
- Weighted scoring system
- Pass/fail determination

## Integrations

The system integrates with:
- **OpenCode**: Skill detection and invocation
- **AutoDev**: Tournament-based competition
- **Agent Arena**: Evaluation and comparison

## Data Flow

```
Task Input
    |
    v
Domain Manager -> Selects appropriate domain & skills
    |
    v
Skill Detector -> Validates skill availability
    |
    v
Competition Manager -> Launches multiple agents
    |
    v
Quality Evaluator -> Scores each agent output
    |
    v
Memory System -> Records lessons learned
    |
    v
Winner Selection -> Returns best solution
```

## Adding New Domains

1. Add domain configuration to `configs/default_domains.yaml`
2. Create agent implementations in `src/domains/{domain_name}/`
3. Define evaluation criteria in the domain configuration
4. Add any domain-specific integrations if needed

## Configuration

Configuration is stored in `.openorchestra/config.yaml`:

```yaml
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
  enabled: true
  timeout_seconds: 300
```