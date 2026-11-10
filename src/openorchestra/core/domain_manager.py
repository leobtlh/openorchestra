"""
Domain manager module for OpenOrchestra.

Handles competency domains and their configurations.
"""

import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_DOMAINS_RESOURCE = ("configs", "default_domains.yaml")
DEFAULT_USER_DOMAINS_PATH = ".openorchestra/domains.yaml"


class EvaluationCriteria(BaseModel):
    """Evaluation criteria for a domain."""

    name: str
    weight: float
    test_command: Optional[str] = None


@dataclass
class DomainConfig:
    """Configuration for a competency domain."""

    id: str
    name: str
    description: str
    required_skills: List[str]
    default_agent_count: int
    evaluation_criteria: Dict[str, float]


def _integer_value(value: Any, default: int) -> int:
    """Coerce a configuration value to int, falling back on bad input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid integer value: %r", value)
        return default


def _string_list(value: Any) -> List[str]:
    """Normalise a skill list, accepting a single string as a convenience."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    logger.warning("Ignoring invalid skill list: %r", value)
    return []


def _criterion_pairs(raw: Any) -> list[tuple[Any, Any]]:
    """Flatten mapping and legacy list-of-mappings criteria into pairs."""
    if isinstance(raw, dict):
        return list(raw.items())

    if isinstance(raw, list):
        pairs: list[tuple[Any, Any]] = []
        for entry in raw:
            if isinstance(entry, dict):
                pairs.extend(entry.items())
            else:
                logger.warning("Ignoring invalid evaluation criterion: %r", entry)
        return pairs

    if raw is not None:
        logger.warning("Ignoring unsupported evaluation criteria: %r", raw)
    return []


def _normalise_criteria(raw: Any) -> Dict[str, float]:
    """Accept both mapping and legacy list-of-mappings criteria formats."""
    weights: Dict[str, float] = {}
    for name, weight in _criterion_pairs(raw):
        try:
            value = float(weight)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid criterion weight: %r=%r", name, weight)
            continue
        if value > 0:
            weights[str(name)] = value

    total = sum(weights.values())
    if total <= 0:
        return {}

    # Positive weights are normalised so scoring is predictable.
    return {name: value / total for name, value in weights.items()}


class DomainManager:
    """
    Manage competency domains and their configurations.

    Domains are based on IEEE/SWECOM standards and industry career paths.
    """

    def __init__(
        self,
        domains_path: Optional[str] = None,
        user_domains_path: Optional[str] = None,
        skill_detector: Optional[Any] = None,
    ):
        self.domains_path = domains_path
        self.user_domains_path = (
            DEFAULT_USER_DOMAINS_PATH if user_domains_path is None else user_domains_path
        )
        self._skill_detector = skill_detector
        self._domains: Dict[str, DomainConfig] = {}
        self._load_domains()

    def _default_domains_source(self) -> Optional[Any]:
        try:
            resource = resources.files("openorchestra").joinpath(*DEFAULT_DOMAINS_RESOURCE)
            if resource.is_file():
                return resource
        except (FileNotFoundError, ModuleNotFoundError):
            logger.warning("Packaged default domains configuration not found")

        fallback = Path(__file__).resolve().parent.parent / "configs" / "default_domains.yaml"
        return fallback if fallback.is_file() else None

    def _load_domains(self) -> None:
        source = Path(self.domains_path) if self.domains_path else self._default_domains_source()
        if source is not None:
            self._merge_source(source)

        if self.user_domains_path:
            user_path = Path(self.user_domains_path)
            if user_path.is_file():
                self._merge_source(user_path)

    def _merge_source(self, source: Any) -> None:
        try:
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            logger.warning("Could not load domains from %s: %s", source, exc)
            return

        if not isinstance(data, dict):
            logger.warning("Ignoring domains file without a mapping: %s", source)
            return

        domains = data.get("domains")
        if not isinstance(domains, dict):
            logger.warning("Ignoring domains file without a 'domains' mapping: %s", source)
            return

        for domain_id, domain_data in domains.items():
            if not isinstance(domain_data, dict):
                logger.warning("Ignoring invalid domain %r in %s", domain_id, source)
                continue

            self._domains[str(domain_id)] = DomainConfig(
                id=str(domain_id),
                name=str(domain_data.get("name", domain_id)),
                description=str(domain_data.get("description", "")),
                required_skills=_string_list(domain_data.get("required_skills")),
                default_agent_count=_integer_value(domain_data.get("default_agent_count"), 3),
                evaluation_criteria=_normalise_criteria(domain_data.get("evaluation_criteria", {})),
            )

    def list_domains(self) -> List[DomainConfig]:
        """List all available domains."""
        return list(self._domains.values())

    def get_domain(self, domain_id: str) -> Optional[DomainConfig]:
        """Get a specific domain by ID."""
        return self._domains.get(domain_id)

    def is_domain_available(self, domain_id: str) -> bool:
        """Check whether all required skills for a domain are available."""
        domain = self.get_domain(domain_id)
        if domain is None:
            return False

        if self._skill_detector is None:
            from openorchestra.core.skill_detector import SkillDetector

            self._skill_detector = SkillDetector()

        installed_skills = self._skill_detector.detect_installed_skills()
        return all(
            skill in installed_skills and installed_skills[skill].available
            for skill in domain.required_skills
        )

    def get_available_domains(self) -> List[DomainConfig]:
        """Get domains with all required skills available."""
        return [domain for domain in self._domains.values() if self.is_domain_available(domain.id)]
