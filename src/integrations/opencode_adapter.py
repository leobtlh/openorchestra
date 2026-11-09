"""
OpenCode adapter module.

Provides integration with OpenCode for skill detection and execution.
"""

import asyncio
import subprocess
import tempfile
import os
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
        return [
            "clean-code",
            "ui-ux-pro-max", 
            "design-taste-frontend",
            "test-driven-development",
            "system-design"
        ]

    def invoke_skill(self, skill_id: str, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous skill invocation (existing method)"""
        return {
            "skill_id": skill_id,
            "task": task,
            "result": f"[SIMULATED] Skill {skill_id} result for task",
            "tool_calls": [],
            "cost": {"input_tokens": 0, "output_tokens": 0, "USD": 0.0},
            "success": True
        }

    async def execute_skill_task(self, task: str, agent_id: str = "default", timeout: int = 300) -> Dict[str, Any]:
        """
        Execute a skill task asynchronously.
        
        This method simulates execution while maintaining the expected interface.
        """
        await asyncio.sleep(0.1)  # Simulate async delay
        
        return {
            "agent_id": agent_id,
            "solution": f"[SIMULATED {agent_id}] Solution for: {task[:100]}...",
            "success": True,
            "execution_time": 0.1,
            "tokens_used": 500,
            "cost": {"USD": 0.01}
        }

    async def run_parallel_tasks(self, tasks: List[str], agent_count: int, timeout: int = 300) -> List[Dict[str, Any]]:
        """
        Run multiple agent tasks in parallel.
        """
        async def execute_single(task_str: str, index: int) -> Dict[str, Any]:
            return await self.execute_skill_task(
                task=task_str,
                agent_id=f"agent_{index+1}",
                timeout=timeout
            )
        
        # Create tasks
        coroutines = [
            execute_single(task, i) 
            for i in range(agent_count)
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Process results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "agent_id": f"agent_{i+1}",
                    "solution": "",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed.append(result)
        
        return processed

    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific skill"""
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