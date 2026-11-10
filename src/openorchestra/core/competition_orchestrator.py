"""
Core orchestration logic for AI agent competitions.

Implements the complete workflow: prepare -> execute -> evaluate -> select -> learn.
"""

import asyncio
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from openorchestra.evaluators.quality_evaluator import QualityEvaluator
from openorchestra.integrations.autodev_adapter import AutoDevAdapter
from openorchestra.integrations.opencode_adapter import OpenCodeAdapter
from openorchestra.memory.competition_memory import CompetitionMemory

from .config import load_config
from .domain_manager import DomainManager
from .hierarchical_learner import HierarchicalLearner
from .optimizer import AgentOptimizer

logger = logging.getLogger(__name__)

MAX_AGENTS_PER_COMPETITION = 5


def _section(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}


def _int_value(section: Dict[str, Any], name: str, default: int) -> int:
    try:
        return int(section.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_value(section: Dict[str, Any], name: str, default: float) -> float:
    try:
        return float(section.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class CompetitionResult:
    """Result of a competition run."""

    winner: Optional[str]
    total_score: float
    agent_results: List[Dict[str, Any]]
    competition_id: str
    execution_time: float
    cost_estimate: float
    patterns_learned: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "competition_id": self.competition_id,
            "winner": self.winner,
            "total_score": self.total_score,
            "agent_results": self.agent_results,
            "execution_time": self.execution_time,
            "cost_estimate": self.cost_estimate,
            "patterns_learned": self.patterns_learned,
            "timestamp": self.timestamp,
        }


@dataclass
class CompetitionConfig:
    """Configuration for running a competition."""

    domain: str
    task_description: str
    agent_count: int = 3
    timeout_per_agent: int = 300
    use_opencode: bool = True
    use_autodev: bool = False
    record_memory: bool = True
    dry_run: bool = False
    optimize: bool = False
    task_complexity: float = 0.5
    budget_tokens: Optional[int] = None
    budget_usd: Optional[float] = None
    simulate: Optional[bool] = None


class CompetitionOrchestrator:
    """
    Orchestrate AI agent competitions with automatic optimisation,
    evaluation, and learning from past competitions.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        memory: Optional[CompetitionMemory] = None,
        domain_manager: Optional[DomainManager] = None,
        evaluator: Optional[QualityEvaluator] = None,
        optimizer: Optional[AgentOptimizer] = None,
        opencode_adapter: Optional[OpenCodeAdapter] = None,
        autodev_adapter: Optional[AutoDevAdapter] = None,
    ):
        self.config_path = config_path
        self.project_config = load_config(config_path)

        memory_config = _section(self.project_config, "memory")
        optimization_config = _section(self.project_config, "optimization")
        evaluation_config = _section(self.project_config, "evaluation")
        agents_config = _section(self.project_config, "agents")
        defaults_config = _section(self.project_config, "defaults")
        general_config = _section(self.project_config, "general")

        database_path = str(memory_config.get("database_path", ".openorchestra/memory.db"))
        self.memory = memory or CompetitionMemory(db_path=database_path)
        self.memory_enabled = bool(memory_config.get("enabled", True))

        self.optimizer = optimizer or AgentOptimizer(optimization_config)
        self.evaluator = evaluator or QualityEvaluator(
            quality_threshold=_float_value(evaluation_config, "quality_threshold", 0.7)
        )
        self.domain_manager = domain_manager or DomainManager()
        self.hierarchical_learner = HierarchicalLearner()

        self.default_agent_count = _int_value(defaults_config, "default_agent_count", 3)
        self.default_timeout = _int_value(agents_config, "timeout_per_agent", 300)
        self.default_budget_tokens = _int_value(optimization_config, "budget_limit_tokens", 50000)
        self.default_budget_usd = _float_value(optimization_config, "budget_limit_usd", 50.0)
        self.output_directory = str(general_config.get("output_directory", "./results"))

        self._opencode_adapter = opencode_adapter
        self._autodev_adapter = autodev_adapter

        self.active_competitions: Dict[str, CompetitionResult] = {}
        self._competition_history: List[Dict[str, Any]] = []

    def _get_opencode_adapter(self, simulate: Optional[bool]) -> OpenCodeAdapter:
        if self._opencode_adapter is None:
            return OpenCodeAdapter(simulate=simulate)
        return self._opencode_adapter

    def _get_autodev_adapter(self) -> AutoDevAdapter:
        if self._autodev_adapter is None:
            self._autodev_adapter = AutoDevAdapter()
        return self._autodev_adapter

    def _validate_config(self, config: CompetitionConfig) -> None:
        """Validate a competition configuration before execution."""
        if not config.task_description.strip():
            raise ValueError("task_description must not be empty")

        if self.domain_manager.get_domain(config.domain) is None:
            raise ValueError(f"Unknown domain: {config.domain}")

        if not config.use_opencode and not config.use_autodev:
            raise ValueError("At least one execution backend must be selected")

    async def run_competition(self, config: CompetitionConfig) -> CompetitionResult:
        """Execute the complete competition workflow."""
        start_time = datetime.now()
        competition_id = f"comp_{uuid.uuid4().hex[:12]}"

        self._validate_config(config)
        agent_count = self._resolve_agent_count(config)
        logger.info(
            "Starting competition %s (domain=%s, agents=%s)",
            competition_id,
            config.domain,
            agent_count,
        )

        if config.dry_run:
            logger.warning("DRY RUN MODE - No actual execution")
            return self._create_dry_run_result(competition_id, config, agent_count)

        task_description = await self._prepare_task(config)
        agent_outputs = await self._launch_agents(task_description, agent_count, config)
        evaluated_results = await self._evaluate_solutions(
            agent_outputs, config.domain, task_description
        )
        winner_info = self._select_winner(evaluated_results)

        result = CompetitionResult(
            winner=winner_info["agent_id"] if winner_info else None,
            total_score=winner_info["score"] if winner_info else 0.0,
            agent_results=evaluated_results,
            competition_id=competition_id,
            execution_time=(datetime.now() - start_time).total_seconds(),
            cost_estimate=self._estimate_cost(agent_count, config.timeout_per_agent),
        )

        if config.record_memory and self.memory_enabled:
            result.patterns_learned = await self._record_learning(config.domain, result)

        self.active_competitions[competition_id] = result
        self._competition_history.append(
            {
                "id": competition_id,
                "domain": config.domain,
                "timestamp": start_time.isoformat(),
                "agent_count": agent_count,
                "winner_score": result.total_score,
            }
        )

        logger.info("Competition completed with winner score %.2f", result.total_score)
        return result

    def _resolve_agent_count(self, config: CompetitionConfig) -> int:
        if config.optimize:
            return self.optimizer.calculate_optimal_agent_count(
                task_complexity=config.task_complexity,
                budget_tokens=config.budget_tokens,
                budget_usd=config.budget_usd,
            )

        if not 1 <= config.agent_count <= MAX_AGENTS_PER_COMPETITION:
            raise ValueError(f"agent_count must be between 1 and {MAX_AGENTS_PER_COMPETITION}")
        return config.agent_count

    async def _prepare_task(self, config: CompetitionConfig) -> str:
        """Enhance the task description with learned patterns."""
        known_patterns = self.memory.get_context_knowledge(config.domain)
        if not known_patterns.strip():
            return config.task_description

        return (
            f"TASK: {config.task_description}\n\n"
            f"LEARNED CONTEXT FROM PREVIOUS COMPETITIONS:\n{known_patterns}\n\n"
            "APPLY THESE INSIGHTS WHILE SOLVING THE TASK"
        )

    async def _launch_agents(
        self, task: str, agent_count: int, config: CompetitionConfig
    ) -> List[Dict[str, Any]]:
        if config.use_opencode:
            return await self._run_opencode_agents(task, agent_count, config)
        return await self._run_autodev_tournament(task, agent_count, config)

    async def _run_opencode_agents(
        self, task: str, agent_count: int, config: CompetitionConfig
    ) -> List[Dict[str, Any]]:
        adapter = self._get_opencode_adapter(config.simulate)
        coroutines = [
            adapter.execute_skill_task(task, f"agent_{index + 1}", config.timeout_per_agent)
            for index in range(agent_count)
        ]
        outputs = await asyncio.gather(*coroutines, return_exceptions=True)

        processed = []
        for index, output in enumerate(outputs):
            processed.append(self._normalise_output(output, index))
        return processed

    async def _run_autodev_tournament(
        self, task: str, agent_count: int, config: CompetitionConfig
    ) -> List[Dict[str, Any]]:
        adapter = self._get_autodev_adapter()
        try:
            tournament = await adapter.run_tournament_async(task, config.domain, agent_count)
        except Exception as exc:
            return [self._failure_output("autodev", exc, 0)]

        winner = tournament.get("winner")
        success = bool(tournament.get("success")) and winner not in (None, "", "none")
        output: Dict[str, Any] = {
            "agent_id": "autodev",
            "solution": str(winner) if success else "",
            "success": success,
        }
        if not success:
            output["error"] = tournament.get("error", "AutoDev tournament failed")
        return [output]

    @staticmethod
    def _normalise_output(output: Any, index: int) -> Dict[str, Any]:
        agent_id = f"agent_{index + 1}"
        if isinstance(output, BaseException):
            return CompetitionOrchestrator._failure_output(agent_id, output, index)
        if not isinstance(output, dict):
            solution = str(output)
            return {
                "agent_id": agent_id,
                "solution": solution,
                "success": bool(solution.strip()),
                "index": index,
            }

        solution = str(output.get("solution", ""))
        success = bool(output.get("success", True)) and bool(solution.strip())
        result = {**output, "agent_id": output.get("agent_id", agent_id)}
        result["solution"] = solution
        result["success"] = success
        result["index"] = index
        return result

    @staticmethod
    def _failure_output(agent_id: str, error: BaseException, index: int) -> Dict[str, Any]:
        return {
            "agent_id": agent_id,
            "solution": "",
            "success": False,
            "error": str(error),
            "index": index,
        }

    async def _evaluate_solutions(
        self,
        solutions: List[Dict[str, Any]],
        domain: str,
        task: str,
    ) -> List[Dict[str, Any]]:
        domain_config = self.domain_manager.get_domain(domain)
        criteria = domain_config.evaluation_criteria if domain_config else {}
        evaluated = []

        for solution_data in solutions:
            solution = str(solution_data.get("solution", ""))
            if not solution.strip():
                evaluated.append(
                    {
                        **solution_data,
                        "evaluation": {"total": 0.0, "passed": False},
                        "score": 0.0,
                    }
                )
                continue

            try:
                result = self.evaluator.evaluate(
                    solution=solution,
                    agent_id=str(solution_data.get("agent_id", "unknown")),
                    domain=domain,
                    criteria=criteria,
                )
                evaluated.append(
                    {
                        **solution_data,
                        "evaluation": {
                            "total": result.total_score,
                            "criteria": result.criteria_scores,
                            "passed": result.passed,
                        },
                        "score": result.total_score,
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive boundary
                logger.error("Evaluation failed for %s: %s", solution_data.get("agent_id"), exc)
                evaluated.append(
                    {
                        **solution_data,
                        "evaluation": {"total": 0.0, "passed": False, "error": str(exc)},
                        "score": 0.0,
                    }
                )

        return evaluated

    @staticmethod
    def _select_winner(
        evaluated_results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        valid_results = [
            result
            for result in evaluated_results
            if result.get("success", True) and str(result.get("solution", "")).strip()
        ]
        if not valid_results:
            return None

        winner = max(valid_results, key=lambda result: float(result.get("score", 0.0)))
        logger.info(
            "Winner selected: %s with score %.2f",
            winner.get("agent_id"),
            float(winner.get("score", 0.0)),
        )
        return {
            "agent_id": winner.get("agent_id"),
            "score": float(winner.get("score", 0.0)),
            "evaluation": winner.get("evaluation"),
        }

    async def _record_learning(self, domain: str, result: CompetitionResult) -> int:
        """Record the competition outcome and learn from successful solutions."""
        self.memory.record_competition_outcome(
            domain=domain,
            agent_count=len(result.agent_results),
            winner_agent=result.winner or "none",
            best_score=result.total_score,
            total_cost_usd=result.cost_estimate,
        )

        learned = 0
        for agent_result in result.agent_results:
            solution = str(agent_result.get("solution", "")).strip()
            if not agent_result.get("success") or not solution:
                continue

            score = float(agent_result.get("score", 0.0))
            pattern_type = self._infer_pattern_type(domain, solution)
            self.memory.record_pattern(
                domain=domain,
                pattern_type=pattern_type,
                description=f"Solution pattern with score {score:.2f}",
                solution=solution[:500],
                confidence=min(0.95, max(0.55, score)),
            )
            self.hierarchical_learner.learn_from_competition(
                domain=domain,
                agent_id=str(agent_result.get("agent_id", "unknown")),
                pattern_type=pattern_type,
                solution=solution[:500],
                score=score,
                is_winning=agent_result.get("agent_id") == result.winner,
            )
            learned += 1

        return learned

    @staticmethod
    def _infer_pattern_type(domain: str, solution: str) -> str:
        pattern_keywords = {
            "backend": ["security", "database", "api", "performance", "error"],
            "frontend_ui_ux": ["accessibility", "responsive", "design", "component", "layout"],
            "devops_cloud": ["deployment", "monitoring", "scaling", "infrastructure", "error"],
            "security": ["vulnerability", "injection", "auth", "encryption", "threat"],
            "data_ml": ["pipeline", "model", "training", "data", "feature"],
            "qa_testing": ["test", "coverage", "mock", "assertion", "validation"],
            "architecture": ["design", "pattern", "scalability", "structure", "modularity"],
            "agent_orchestration": ["coordination", "tournament", "evaluation", "selection"],
            "code_refinement": ["optimization", "refactor", "improvement", "bug", "quality"],
        }
        solution_lower = solution.lower()
        for keyword in pattern_keywords.get(domain, ["general"]):
            if keyword in solution_lower:
                return keyword
        return "general"

    @staticmethod
    def _estimate_cost(agent_count: int, timeout: int) -> float:
        """Estimate cost in USD (2000 tokens per minute of agent time)."""
        minute_blocks = max(1, math.ceil(timeout / 60))
        total_tokens = agent_count * 2000 * minute_blocks
        return (total_tokens / 1000) * 0.03

    def _create_dry_run_result(
        self, competition_id: str, config: CompetitionConfig, agent_count: int
    ) -> CompetitionResult:
        return CompetitionResult(
            winner=None,
            total_score=0.0,
            agent_results=[
                {
                    "agent_id": f"dummy_agent_{index + 1}",
                    "solution": "[DRY RUN - No solution]",
                    "success": False,
                }
                for index in range(agent_count)
            ],
            competition_id=competition_id,
            execution_time=0.0,
            cost_estimate=0.0,
        )

    def get_competition_history(
        self, domain: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get competition history, optionally filtered by domain."""
        if domain:
            matching = [
                entry for entry in self._competition_history if entry.get("domain") == domain
            ]
            return matching[-limit:]
        return self._competition_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        memory_stats = self.memory.get_stats()
        return {
            "active_competitions": len(self.active_competitions),
            "total_competitions_run": len(self._competition_history),
            "domains_supported": len(self.domain_manager.list_domains()),
            "patterns_in_memory": memory_stats["patterns_stored"],
        }
