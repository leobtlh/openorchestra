"""
Integrations module for OpenOrchestra.

Provides adapters for external tools and platforms.
"""

from openorchestra.integrations.opencode_adapter import OpenCodeAdapter
from openorchestra.integrations.autodev_adapter import AutoDevAdapter
from openorchestra.integrations.agent_arena_bridge import AgentArenaBridge

__all__ = ["OpenCodeAdapter", "AutoDevAdapter", "AgentArenaBridge"]