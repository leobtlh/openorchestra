"""
OpenOrchestra - Multi-agent orchestrator for code generation and evaluation.

This package provides tools for running competitions among multiple AI coding agents
with objective evaluation and persistent memory for learning.
"""

__version__ = "0.1.0"
__author__ = "OpenOrchestra Contributors"

from openorchestra.core.skill_detector import SkillDetector, SkillInfo
from openorchestra.core.domain_manager import DomainManager, DomainConfig
from openorchestra.memory.competition_memory import CompetitionMemory

__all__ = [
    "SkillDetector",
    "SkillInfo", 
    "DomainManager",
    "DomainConfig",
    "CompetitionMemory",
    "__version__",
    "__author__",
]