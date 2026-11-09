"""
OpenCode adapter module.

Provides integration with OpenCode for skill detection and execution.
"""

import subprocess
from typing import List, Optional, Dict, Any
from pathlib import Path


class OpenCodeAdapter:
    """
    Adapter for OpenCode integration.
    
    Handles skill detection, invocation, and result retrieval.
    """

    def __init__(self, opencode_path: str = "opencode"):
        self.opencode_path = opencode_path
        self._check_installation()

    def _check_installation(self) -> bool:
        """Check if OpenCode is installed"""
        try:
            result = subprocess.run(
                [self.opencode_path, "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def detect_skills(self) -> List[str]:
        """Detect available skills in OpenCode"""
        # This would query OpenCode's skill registry
        # For now, return a placeholder
        return [
            "clean-code",
            "ui-ux-pro-max", 
            "design-taste-frontend",
            "test-driven-development"
        ]

    def invoke_skill(self, skill_id: str, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke a skill with a task.
        
        Args:
            skill_id: The skill to invoke
            task: The task description
            context: Optional context/instructions
            
        Returns:
            Dict with result, tool_calls, and cost information
        """
        # This would execute the skill in OpenCode
        # For now, return a placeholder structure
        return {
            "skill_id": skill_id,
            "task": task,
            "result": "Skill execution result placeholder",
            "tool_calls": [],
            "cost": {"input_tokens": 0, "output_tokens": 0, "USD": 0.0},
            "success": True
        }

    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific skill"""
        # This would query skill metadata
        skill_info = {
            "clean-code": {
                "name": "Clean Code Principles",
                "version": "2.0",
                "domains": ["backend", "code_refinement"],
                "description": "Implements clean code principles and best practices"
            },
            "ui-ux-pro-max": {
                "name": "UI/UX Pro Max",
                "version": "1.5",
                "domains": ["frontend_ui_ux", "design"],
                "description": "Advanced UI/UX design and implementation"
            }
        }
        return skill_info.get(skill_id)