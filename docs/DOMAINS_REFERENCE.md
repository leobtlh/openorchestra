# Domain Reference

OpenOrchestra ships nine competency domains. Each domain defines the skills an
agent should use, a default agent count, and a set of weighted evaluation
criteria.

The built-in definitions live in
[`src/openorchestra/configs/default_domains.yaml`](../src/openorchestra/configs/default_domains.yaml).
User-defined domains are merged on top of them from
`.openorchestra/domains.yaml`.

## Criteria normalisation

Weights may be written as a YAML mapping:

```yaml
evaluation_criteria:
  code_quality: 0.3
  security_standards: 0.25
  maintainability: 0.1
```

The legacy list form is also accepted:

```yaml
evaluation_criteria:
  - code_quality: 0.3
  - security_standards: 0.25
```

`DomainManager` normalises all positive weights so they sum to `1.0`. Invalid
or non-positive weights are ignored. A domain with no valid criteria gets an
empty criteria mapping, and every solution scores `0.0` for that domain.

## Built-in domains

### `backend` — Backend Development

Backend development, security, databases, and API design.

| Criterion | Weight |
|-----------|--------|
| `code_quality` | 0.30 |
| `security_standards` | 0.25 |
| `database_design` | 0.20 |
| `api_efficiency` | 0.15 |
| `maintainability` | 0.10 |

Required skills: `clean-code`, `system-design`.

### `frontend_ui_ux` — Frontend Development & UI/UX

Frontend development, UX design, design systems, and accessibility.

| Criterion | Weight |
|-----------|--------|
| `design_system_compliance` | 0.35 |
| `accessibility_standards` | 0.25 |
| `responsive_behavior` | 0.20 |
| `code_quality` | 0.10 |
| `performance` | 0.10 |

Required skills: `ui-ux-pro-max`, `design-taste-frontend`.

### `devops_cloud` — DevOps & Cloud

Infrastructure, CI/CD, orchestration, and cloud platforms.

| Criterion | Weight |
|-----------|--------|
| `infrastructure_efficiency` | 0.30 |
| `security_compliance` | 0.25 |
| `monitoring_coverage` | 0.20 |
| `deployment_reliability` | 0.15 |
| `cost_optimization` | 0.10 |

Required skills: `devops-engineer`, `cloud-architecture`.

### `security` — Application Security

Application security, penetration testing, and compliance.

| Criterion | Weight |
|-----------|--------|
| `vulnerability_count` | 0.35 |
| `security_best_practices` | 0.30 |
| `compliance_standards` | 0.20 |
| `threat_modeling` | 0.15 |

Required skills: `secure-coding`, `pentesting`.

### `data_ml` — Data Engineering & Machine Learning

Data pipelines, machine learning, and data quality.

| Criterion | Weight |
|-----------|--------|
| `pipeline_reliability` | 0.30 |
| `data_quality` | 0.25 |
| `model_accuracy` | 0.25 |
| `scalability` | 0.20 |

Required skills: `data-engineering`, `ml-engineer`.

### `qa_testing` — Quality Assurance & Testing

Automated testing, quality assurance, and coverage analysis.

| Criterion | Weight |
|-----------|--------|
| `test_coverage` | 0.30 |
| `test_quality` | 0.25 |
| `bug_detection_rate` | 0.25 |
| `automation_effectiveness` | 0.20 |

Required skills: `test-driven-development`, `testing-strategies`.

### `architecture` — System Architecture

System design, scalability, patterns, and technical decisions.

| Criterion | Weight |
|-----------|--------|
| `scalability_design` | 0.30 |
| `fault_tolerance` | 0.25 |
| `maintainability` | 0.25 |
| `technology_selection` | 0.20 |

Required skills: `system-design`, `architectural-patterns`.

### `agent_orchestration` — Agent Orchestration

Multi-agent coordination, tournament management, and evaluation.

| Criterion | Weight |
|-----------|--------|
| `competition_design` | 0.30 |
| `agent_specialization` | 0.25 |
| `evaluation_fairness` | 0.25 |
| `learning_effectiveness` | 0.20 |

Required skills: `agentic-delivery`, `tournament-management`.

### `code_refinement` — Code Refinement

Self-refinement, quality improvement, and code optimization.

| Criterion | Weight |
|-----------|--------|
| `quality_improvement` | 0.35 |
| `optimization_efficiency` | 0.30 |
| `consistency` | 0.20 |
| `maintainability_gain` | 0.15 |

Required skills: `clean-code`, `quality-gates`.

## Inspecting domains

```bash
openorchestra list-domains
openorchestra show-domain backend
```

`list-domains` also reports whether all required skills for a domain are
available in the current environment.

## Creating a custom domain

Use the CLI:

```bash
openorchestra create-domain \
  --name "Mobile Development" \
  --id mobile_development \
  --description "Native mobile applications" \
  --skills "swift,kotlin,react-native" \
  --criteria "mobile_performance:0.4,app_store_compliance:0.35,battery_optimization:0.25"
```

The command writes or updates `.openorchestra/domains.yaml`. Criteria without
an explicit `:weight` default to `1.0` before normalisation.

The equivalent programmatic form is:

```python
from openorchestra.core.domain_manager import DomainManager

manager = DomainManager()
domain = manager.get_domain("backend")
assert domain is not None
print(domain.evaluation_criteria)
```

Custom domains with the same ID as a built-in domain override the built-in
definition for the current project.
