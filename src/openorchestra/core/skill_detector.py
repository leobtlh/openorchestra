"""
Skill detection module for OpenOrchestra.

Automatically detects available AI coding skills in the local environment.
"""

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SkillInfo(BaseModel):
    """Information about a detected skill."""

    id: str
    name: str
    version: str
    domains: List[str]
    available: bool = True
    path: Optional[str] = None


class SkillDetector:
    """
    Detect available skills in the environment.

    Skills are looked up in OpenCode skill directories, the current project,
    and any explicitly configured search paths.
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

    CORE_SKILLS = {
        "clean-code",
        "test-driven-development",
        "system-design",
        "agentic-delivery",
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        search_paths: Optional[Iterable[str | Path]] = None,
        default_skills: Optional[Dict[str, str]] = None,
    ):
        self.config_path = config_path or ".openorchestra/config.yaml"
        self.default_skills = default_skills or dict(self.DEFAULT_SKILLS)
        self.search_paths = [Path(path).expanduser() for path in (search_paths or [])]
        if search_paths is None:
            self.search_paths = [
                Path("~/.config/opencode/skills").expanduser(),
                Path("~/.opencode/skills").expanduser(),
                Path.cwd() / "skills",
            ]
        self._detected_skills: Dict[str, SkillInfo] = {}

    def detect_installed_skills(self) -> Dict[str, SkillInfo]:
        """Detect all installed skills in the environment."""
        skills: Dict[str, SkillInfo] = {}

        for skill_id, skill_name in self.default_skills.items():
            skills[skill_id] = SkillInfo(
                id=skill_id,
                name=skill_name,
                version="installed",
                domains=[],
                available=self._check_skill_available(skill_id),
                path=self._find_skill_path(skill_id),
            )

        skills.update(self._load_custom_skills())
        self._detected_skills = skills
        return skills

    def _check_skill_available(self, skill_id: str) -> bool:
        """Check whether a skill exists in one of the search paths."""
        if self._find_skill_path(skill_id) is not None:
            return True

        # Core skills are built into OpenOrchestra's default workflow.
        return skill_id in self.CORE_SKILLS

    def _find_skill_path(self, skill_id: str) -> Optional[str]:
        """Find the path to a skill directory or markdown file."""
        for base in self.search_paths:
            directory = base / skill_id
            if directory.exists():
                return str(directory)

            markdown = base / f"{skill_id}.md"
            if markdown.is_file():
                return str(markdown)

        return None

    def _load_custom_skills(self) -> Dict[str, SkillInfo]:
        """Load custom skill declarations from configuration."""
        config_path = Path(self.config_path)
        if not config_path.is_file():
            return {}

        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            logger.warning("Could not read custom skills from %s: %s", config_path, exc)
            return {}

        if not isinstance(config, dict):
            return {}

        custom_skills = config.get("custom_skills", [])
        if not isinstance(custom_skills, list):
            logger.warning("Ignoring non-list 'custom_skills' in %s", config_path)
            return {}

        skills: Dict[str, SkillInfo] = {}
        for entry in custom_skills:
            if not isinstance(entry, dict) or "id" not in entry:
                logger.warning("Ignoring invalid custom skill entry: %r", entry)
                continue

            skill_id = str(entry["id"])
            skills[skill_id] = SkillInfo(
                id=skill_id,
                name=str(entry.get("name", skill_id)),
                version=str(entry.get("version", "custom")),
                domains=list(entry.get("domains", []) or []),
                available=bool(entry.get("available", True)),
                path=entry.get("path"),
            )

        return skills

    def get_available_domains(self) -> List[str]:
        """Get the IDs of domains whose required skills are all available."""
        from openorchestra.core.domain_manager import DomainManager

        manager = DomainManager(skill_detector=self)
        return [
            domain.id for domain in manager.list_domains() if manager.is_domain_available(domain.id)
        ]

    def get_required_skills(self, domain: str) -> List[str]:
        """Get the skill IDs required by a domain."""
        from openorchestra.core.domain_manager import DomainManager

        domain_info = DomainManager(skill_detector=self).get_domain(domain)
        return list(domain_info.required_skills) if domain_info else []
