"""
OpenOrchestra - Multi-agent orchestrator for code generation and evaluation.

This package provides tools for running competitions among multiple AI coding
agents with objective evaluation and persistent memory for learning.
"""

from openorchestra.core.competition_orchestrator import (
    CompetitionConfig,
    CompetitionOrchestrator,
    CompetitionResult,
)
from openorchestra.core.domain_manager import DomainConfig, DomainManager
from openorchestra.core.skill_detector import SkillDetector, SkillInfo
from openorchestra.memory.competition_memory import CompetitionMemory

__version__ = "0.1.0"
__author__ = "OpenOrchestra Contributors"

__all__ = [
    "SkillDetector",
    "SkillInfo",
    "DomainManager",
    "DomainConfig",
    "CompetitionMemory",
    "CompetitionOrchestrator",
    "CompetitionConfig",
    "CompetitionResult",
    "__version__",
    "__author__",
]
