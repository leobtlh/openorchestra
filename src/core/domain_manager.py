"""
Domain manager module for OpenOrchestra.

Handles competency domains and their configurations.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel
import yaml


class EvaluationCriteria(BaseModel):
    """Evaluation criteria for a domain"""
    name: str
    weight: float
    test_command: Optional[str] = None


@dataclass
class DomainConfig:
    """Configuration for a competency domain"""
    id: str
    name: str
    description: str
    required_skills: List[str]
    default_agent_count: int
    evaluation_criteria: Dict[str, float]


class DomainManager:
    """
    Manages competency domains and their configurations.
    
    Domains are based on IEEE/SWECOM standards and industry career paths.
    """

    DEFAULT_DOMAINS_PATH = "configs/default_domains.yaml"

    def __init__(self, domains_path: Optional[str] = None):
        self.domains_path = domains_path or self.DEFAULT_DOMAINS_PATH
        self._domains: Dict[str, DomainConfig] = {}
        self._load_domains()

    def _load_domains(self) -> None:
        """Load domains from configuration file"""
        full_path = Path(self.domains_path)
        if not full_path.exists():
            full_path = Path("src") / self.DEFAULT_DOMAINS_PATH
        
        if full_path.exists():
            with open(full_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'domains' in data:
                    for domain_id, domain_data in data['domains'].items():
                        self._domains[domain_id] = DomainConfig(
                            id=domain_id,
                            name=domain_data.get('name', domain_id),
                            description=domain_data.get('description', ''),
                            required_skills=domain_data.get('required_skills', []),
                            default_agent_count=domain_data.get('default_agent_count', 5),
                            evaluation_criteria=domain_data.get('evaluation_criteria', {})
                        )

    def list_domains(self) -> List[DomainConfig]:
        """List all available domains"""
        return list(self._domains.values())

    def get_domain(self, domain_id: str) -> Optional[DomainConfig]:
        """Get a specific domain by ID"""
        return self._domains.get(domain_id)

    def is_domain_available(self, domain_id: str) -> bool:
        """Check if a domain has all required skills available"""
        from openorchestra.core.skill_detector import SkillDetector
        
        domain = self.get_domain(domain_id)
        if not domain:
            return False

        detector = SkillDetector()
        installed_skills = detector.detect_installed_skills()

        for required_skill in domain.required_skills:
            if required_skill not in installed_skills:
                return False
            if not installed_skills[required_skill].available:
                return False

        return True

    def get_available_domains(self) -> List[DomainConfig]:
        """Get domains with all required skills available"""
        return [
            domain for domain in self._domains.values()
            if self.is_domain_available(domain.id)
        ]