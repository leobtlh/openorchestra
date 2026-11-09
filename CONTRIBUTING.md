# Contributing to OpenOrchestra

Thank you for your interest in contributing to OpenOrchestra! This document provides guidelines and instructions for contributors.

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Install pre-commit hooks (recommended):
   ```bash
   pre-commit install
   ```

## Code Style

We follow PEP 8 and use the following tools:

- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking

Before submitting a pull request, run:

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type check
mypy src/
```

## Testing

1. Run the test suite:
   ```bash
   pytest -v
   ```

2. Run tests with coverage:
   ```bash
   pytest --cov=openorchestra --cov-report=html
   ```

3. All tests must pass at 100% coverage for new code.

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request with a clear description

## Architectural Patterns

### Domain Modules

Each domain follows this structure:

```python
# src/domains/backend/
├── __init__.py        # Domain configuration
├── agents/             # Specialist agents
│   ├── api_builder.py
│   ├── database_designer.py
│   └── security_analyzer.py
├── evaluators/         # Domain-specific evaluation
│   └── code_quality.py
└── presets/            # Default configurations
    └── default.yaml
```

### Skill Integration

Skills should be detected dynamically:

```python
from openorchestra.core.skill_detector import SkillDetector

detector = SkillDetector()
available_skills = detector.detect_installed_skills()
```

### Memory Usage

Use the memory system for learning:

```python
from openorchestra.memory.competition_memory import CompetitionMemory

memory = CompetitionMemory()
memory.record_pattern(domain="backend", pattern_solution="...")
```

## Questions?

Open an issue on GitHub or contact the maintainers.

## License

By contributing, you agree that your contributions will be licensed under GPL-3.0.