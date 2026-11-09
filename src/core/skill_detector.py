"""
Skill detection module for OpenOrchestra.

This module handles automatic detection of available AI coding skills
in the OpenCode environment.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import yaml


class SkillInfo(BaseModel):
    """Information about a detected skill"""
    id: str
    name: str
    version: str
    domains: List[str]
    available: bool = True
    path: Optional[str] = None


class SkillDetector:
    """
    Detects available skills in the environment.
    
    Skills can be found in:
    - OpenCode skill directories
    - Plugin directories
    - Custom skill paths
    """

    DEFAULT_SKILLS: Dict[str, str] = {
        "clean-code": "Clean Code Principles",
        "ui-ux-pro-max": "UI/UX Pro Max",
        "design-taste-frontend": "Design Taste Frontend",
        "test-driven-development": "Test-Driven Development",
        "system-design": "System Design",
        "devops-engineer": "DevOps Engineer",
        "secure-coding": "Secure Coding Practices",
        "data-engineering": "Data Engineering",
        "ml-engineer": "Machine Learning Engineer",
        "agentic-delivery": "Agentic Delivery Framework",
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or ".openorchestra/config.yaml"
        self._detected_skills: Dict[str, SkillInfo] = {}

    def detect_installed_skills(self) -> Dict[str, SkillInfo]:
        """
        Detect all installed skills in the environment.
        
        Returns:
            Dict mapping skill IDs to their information
        """
        skills: Dict[str, SkillInfo] = {}

        # Check default skills availability
        for skill_id, skill_name in self.DEFAULT_SKILLS.items():
            skills[skill_id] = SkillInfo(
                id=skill_id,
                name=skill_name,
                version="installed",
                domains=[],
                available=self._check_skill_available(skill_id),
                path=self._find_skill_path(skill_id)
            )

        # Check for custom skills from config
        custom_skills = self._load_custom_skills()
        skills.update(custom_skills)

        self._detected_skills = skills
        return skills

    def _check_skill_available(self, skill_id: str) -> bool:
        """Check if a skill is available in the environment"""
        # Check OPencode skill directories
        opencode_paths = [
            os.path.expanduser("~/.config/opencode/skills"),
            os.path.expanduser("~/.opencode/skills"),
        ]

        for path in opencode_paths:
            skill_path = Path(path) / skill_id
            if skill_path.exists():
                return True

        # Check plugin directories
        plugin_paths = [
            "/usr/local/lib/python3.*/site-packages/opencode_schemas/",
            "./.venv/lib/python3.*/site-packages/opencode_schemas/",
        ]

        for pattern in plugin_paths:
            for path in Path(".").glob(pattern):
                if (path / skill_id).exists():
                    return True

        # For now, mark core skills as available
        # In production, this would check actual installation
        core_skills = [
            "clean-code", "test-driven-development", 
            "system-design", "agentic-delivery"
        ]
        if skill_id in core_skills:
            return True

        return False

    def _find_skill_path(self, skill_id: str) -> Optional[str]:
        """Find the path to a skill"""
        search_paths = [
            Path("~/.config/opencode/skills").expanduser(),
            Path("~/.opencode/skills").expanduser(),
            Path.cwd() / "skills",
        ]

        for path in search_paths:
            skill_path = path / skill_id
            if skill_path.exists():
                return str(skill_path)

        return None

    def _load_custom_skills(self) -> Dict[str, SkillInfo]:
        """Load custom skills from configuration"""
        custom_skills = {}

        if not os.path.exists(self.config_path):
            return custom_skills

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            if config and 'custom_skills' in config:
                for skill_config in config['custom_skills']:
                    skill_id = skill_config['id']
                    custom_skills[skill_id] = SkillInfo(
                        id=skill_id,
                        name=skill_config.get('name', skill_id),
                        version=skill_config.get('version', 'custom'),
                        domains=skill_config.get('domains', []),
                        available=True,
                        path=skill_config.get('path')
                    )
        except Exception:
            pass

        return custom_skills

    def get_available_domains(self) -> List[str]:
        """
        Get list of domains that have required skills available.
        
        Returns:
            List of available domain names
        """
        from openorchestra.core.domain_manager import DomainManager
        domain_manager = DomainManager()
        all_domains = domain_manager.list_domains()

        available_domains = []
        for domain in all_domains:
            if domain_manager.is_domain_available(domain.id):
                available_domains.append(domain.id)

        return available_domains

    def get_required_skills(self, domain: str) -> List[str]:
        """
        Get list of required skills for a specific domain.
        
        Args:
            domain: The domain identifier
            
        Returns:
            List of required skill IDs
        """
        from openorchestra.core.domain_manager import DomainManager
        domain_manager = DomainManager()
        domain_info = domain_manager.get_domain(domain)

        if domain_info:
            return domain_info.required_skills
        return []