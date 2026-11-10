"""
OpenCode adapter module.

Provides integration with OpenCode for skill detection and headless execution.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from .process import executable_available


class OpenCodeAdapter:
    """
    Adapter for OpenCode integration.

    Headless execution uses ``opencode run --format json``. When the binary is
    unavailable, or when ``simulate=True``, a deterministic simulated result is
    returned so the orchestrator stays usable in CI.
    """

    def __init__(
        self,
        opencode_path: str = "opencode",
        simulate: Optional[bool] = None,
        timeout: int = 300,
    ):
        self.opencode_path = opencode_path
        self.timeout = timeout
        self.available = self._check_installation()
        self.simulate = (not self.available) if simulate is None else simulate

    def _check_installation(self) -> bool:
        """Return True when the OpenCode executable responds to --version."""
        return executable_available(self.opencode_path)

    def detect_skills(self) -> List[str]:
        """Detect available skills through the core skill detector."""
        from openorchestra.core.skill_detector import SkillDetector

        skills = SkillDetector().detect_installed_skills()
        return sorted(skill_id for skill_id, info in skills.items() if info.available)

    def invoke_skill(
        self, skill_id: str, task: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous simulated skill invocation kept for API compatibility."""
        return {
            "skill_id": skill_id,
            "task": task,
            "result": f"[SIMULATED] Skill {skill_id} result for task",
            "tool_calls": [],
            "cost": {"input_tokens": 0, "output_tokens": 0, "USD": 0.0},
            "success": True,
        }

    async def execute_skill_task(
        self, task: str, agent_id: str = "default", timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute a task either live or in deterministic simulation mode."""
        if self.simulate:
            return self._simulated_result(task, agent_id)

        return await self._execute_live(task, agent_id, timeout)

    def _simulated_result(self, task: str, agent_id: str) -> Dict[str, Any]:
        return {
            "agent_id": agent_id,
            "solution": f"[SIMULATED {agent_id}] Solution for: {task[:100]}...",
            "success": True,
            "execution_time": 0.1,
            "tokens_used": 500,
            "cost": {"USD": 0.01},
        }

    async def _execute_live(self, task: str, agent_id: str, timeout: int) -> Dict[str, Any]:
        start_time = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                self.opencode_path,
                "run",
                "--format",
                "json",
                "--auto",
                task,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            return {
                "agent_id": agent_id,
                "solution": "",
                "success": False,
                "error": f"Unable to start OpenCode: {exc}",
                "execution_time": time.time() - start_time,
                "cost": {"USD": 0.0},
            }

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
            return {
                "agent_id": agent_id,
                "solution": "",
                "success": False,
                "error": f"Timeout after {timeout}s",
                "execution_time": time.time() - start_time,
                "cost": {"USD": 0.0},
            }

        solution = self._parse_output(stdout.decode(errors="replace"))
        success = process.returncode == 0 and bool(solution)
        result: Dict[str, Any] = {
            "agent_id": agent_id,
            "solution": solution,
            "success": success,
            "execution_time": time.time() - start_time,
            "tokens_used": 0,
            "cost": {"USD": 0.0},
        }
        if not success:
            result["error"] = stderr.decode(errors="replace").strip() or "OpenCode failed"
        return result

    @staticmethod
    def _parse_output(output: str) -> str:
        """Extract assistant text from OpenCode's JSON event stream."""
        chunks: List[str] = []

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                chunks.append(line)
                continue
            OpenCodeAdapter._collect_text(payload, chunks)

        return "\n".join(chunk for chunk in chunks if chunk).strip()

    @staticmethod
    def _collect_text(payload: Any, chunks: List[str]) -> None:
        if isinstance(payload, str):
            if payload:
                chunks.append(payload)
        elif isinstance(payload, list):
            for item in payload:
                OpenCodeAdapter._collect_text(item, chunks)
        elif isinstance(payload, dict):
            OpenCodeAdapter._collect_from_dict(payload, chunks)

    @staticmethod
    def _collect_from_dict(payload: Dict[str, Any], chunks: List[str]) -> None:
        text = payload.get("text")
        if isinstance(text, str) and text:
            chunks.append(text)

        for key, value in payload.items():
            if key != "text" and isinstance(value, (dict, list)):
                OpenCodeAdapter._collect_text(value, chunks)

    async def run_parallel_tasks(
        self, tasks: List[str], agent_count: int, timeout: int = 300
    ) -> List[Dict[str, Any]]:
        """Run the same task with multiple agent identities in parallel."""

        async def execute_single(task_str: str, index: int) -> Dict[str, Any]:
            return await self.execute_skill_task(
                task=task_str,
                agent_id=f"agent_{index + 1}",
                timeout=timeout,
            )

        coroutines = (
            [execute_single(tasks[index % len(tasks)], index) for index in range(agent_count)]
            if tasks
            else []
        )
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        processed: List[Dict[str, Any]] = []
        for index, result in enumerate(results):
            if isinstance(result, BaseException):
                processed.append(
                    {
                        "agent_id": f"agent_{index + 1}",
                        "solution": "",
                        "success": False,
                        "error": str(result),
                    }
                )
            else:
                processed.append(result)

        return processed

    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get static information about a specific skill."""
        skill_info = {
            "clean-code": {
                "name": "Clean Code Principles",
                "version": "2.0",
                "domains": ["backend", "code_refinement"],
                "description": "Implements clean code principles and best practices",
            },
            "ui-ux-pro-max": {
                "name": "UI/UX Pro Max",
                "version": "1.5",
                "domains": ["frontend_ui_ux", "design"],
                "description": "Advanced UI/UX design and implementation",
            },
        }
        return skill_info.get(skill_id)
