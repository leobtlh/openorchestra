"""
Core orchestration logic for AI agent competitions.

Implements the complete workflow: prepare → execute → evaluate → select → learn
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field

from .optimizer import AgentOptimizer
from .domain_manager import DomainManager
from .pattern_signature import PatternSignature
from openorchestra.memory.competition_memory import CompetitionMemory
from openorchestra.evaluators.quality_evaluator import QualityEvaluator
from openorchestra.integrations.opencode_adapter import OpenCodeAdapter
from openorchestra.integrations.autodev_adapter import AutoDevAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CompetitionResult:
    """Result of a competition run"""
    winner: Optional[str]
    total_score: float
    agent_results: List[Dict[str, Any]]
    competition_id: str
    execution_time: float
    cost_estimate: float
    patterns_learned: int = 0


@dataclass
class CompetitionConfig:
    """Configuration for running competitions"""
    domain: str
    task_description: str
    agent_count: int = 3
    timeout_per_agent: int = 300
    use_opencode: bool = True
    use_autodev: bool = False
    record_memory: bool = True
    dry_run: bool = False


class CompetitionOrchestrator:
    """
    Orchestrates AI agent competitions with automatic optimization,
    evaluation, and learning from past competitions.
    """

    def __init__(self, config_path: Optional[str] = None):
        # Core components
        self.memory = CompetitionMemory()
        self.optimizer = AgentOptimizer()
        self.evaluator = QualityEvaluator()
        self.domain_manager = DomainManager()
        
        # Integrators (loaded on demand)
        self._opencode_adapter = None
        self._autodev_adapter = None
        
        # Competition state
        self.active_competitions: Dict[str, CompetitionResult] = {}
        self._competition_history: List[Dict[str, Any]] = []

    def _get_opencode_adapter(self) -> OpenCodeAdapter:
        """Lazy load OpenCode adapter"""
        if self._opencode_adapter is None:
            self._opencode_adapter = OpenCodeAdapter()
        return self._opencode_adapter

    def _get_autodev_adapter(self) -> AutoDevAdapter:
        """Lazy load AutoDev adapter"""
        if self._autodev_adapter is None:
            self._autodev_adapter = AutoDevAdapter()
        return self._autodev_adapter

    async def run_competition(self, config: CompetitionConfig) -> CompetitionResult:
        """
        Execute a complete competition workflow:
        1. Prepare prompts with learned context
        2. Dispatch agents via adapters
        3. Evaluate solutions
        4. Select winner
        5. Record learning
        """
        start_time = datetime.now()
        competition_id = f"comp_{int(start_time.timestamp())}"
        
        logger.info(f"Starting competition {competition_id}")
        logger.info(f"Domain: {config.domain}, Agents: {config.agent_count}")
        
        if config.dry_run:
            logger.warning("DRY RUN MODE - No actual execution")
            return self._create_dry_run_result(competition_id, config)
        
        try:
            # Step 1: Prepare enhanced task with learned patterns
            task_description = await self._prepare_task(config)
            
            # Step 2: Launch competing agents
            agent_outputs = await self._launch_agents(
                task_description, 
                config.agent_count, 
                config
            )
            
            # Step 3: Evaluate all solutions
            evaluated_results = await self._evaluate_solutions(
                agent_outputs, 
                config.domain, 
                task_description
            )
            
            # Step 4: Select winner
            winner_info = self._select_winner(evaluated_results)
            
            result = CompetitionResult(
                winner=winner_info['agent_id'] if winner_info else None,
                total_score=winner_info['score'] if winner_info else 0.0,
                agent_results=evaluated_results,
                competition_id=competition_id,
                execution_time=(datetime.now() - start_time).total_seconds(),
                cost_estimate=self._estimate_cost(config.agent_count, config.timeout_per_agent)
            )
            
            # Step 5: Record learning
            if config.record_memory:
                await self._record_learning(config.domain, result)
                result.patterns_learned = len(self.memory.get_lessons_for_domain(config.domain))
            
            # Store result
            self.active_competitions[competition_id] = result
            self._competition_history.append({
                'id': competition_id,
                'domain': config.domain,
                'timestamp': start_time.isoformat(),
                'agent_count': config.agent_count,
                'winner_score': result.total_score
            })
            
            logger.info(f"Competition completed: Winner score = {result.total_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Competition failed: {str(e)}")
            raise

    async def _prepare_task(self, config: CompetitionConfig) -> str:
        """Enhance task description with learned patterns and context"""
        # Get relevant patterns from memory
        known_patterns = self.memory.get_context_knowledge(config.domain)
        
        # Build enhanced task
        enhanced_task = config.task_description
        
        if known_patterns and known_patterns.strip():
            enhanced_task = (
                f"TASK: {config.task_description}\n\n"
                f"LEARNED CONTEXT FROM PREVIOUS COMPETITIONS:\n{known_patterns}\n\n"
                f"APPLY THESE INSIGHTS WHILE SOLVING THE TASK"
            )
        
        return enhanced_task

    async def _launch_agents(
        self, 
        task: str, 
        agent_count: int, 
        config: CompetitionConfig
    ) -> List[Dict[str, Any]]:
        """Launch multiple agent instances via configured adapters"""
        agent_outputs = []
        
        # Create tasks for parallel execution
        async_tasks = []
        
        for i in range(agent_count):
            agent_id = f"agent_{i+1}"
            if config.use_opencode:
                adapter = self._get_opencode_adapter()
                async_tasks.append(
                    adapter.execute_skill_task(task, agent_id, config.timeout_per_agent)
                )
            elif config.use_autodev:
                adapter = self._get_autodev_adapter()
                async_tasks.append(
                    adapter.run_tournament(task, config.domain, agent_count)
                )
        
        if async_tasks:
            # Execute all agents in parallel with timeout
            try:
                agent_outputs = await asyncio.gather(
                    *async_tasks,
                    return_exceptions=True
                )
            except Exception as e:
                logger.warning(f"Some agents failed: {str(e)}")
        
        # Process results
        processed_outputs = []
        for i, output in enumerate(agent_outputs):
            if isinstance(output, Exception):
                processed_outputs.append({
                    'agent_id': f"agent_{i+1}",
                    'solution': '',
                    'error': str(output),
                    'success': False
                })
            else:
                processed_outputs.append(output if isinstance(output, dict) else {
                    'agent_id': f"agent_{i+1}",
                    'solution': str(output),
                    'success': True
                })
        
        return processed_outputs

    async def _evaluate_solutions(
        self, 
        solutions: List[Dict[str, Any]], 
        domain: str,
        task: str
    ) -> List[Dict[str, Any]]:
        """Evaluate each solution against domain criteria"""
        evaluated = []
        
        # Get domain configuration
        domain_config = self.domain_manager.get_domain(domain)
        criteria = domain_config.evaluation_criteria if domain_config else {}
        
        for solution_data in solutions:
            solution = solution_data.get('solution', '')
            
            # Skip empty solutions
            if not solution.strip():
                evaluated.append({
                    **solution_data,
                    'evaluation': {'total': 0.0, 'passed': False},
                    'score': 0.0
                })
                continue
            
            try:
                result = self.evaluator.evaluate(
                    solution=solution,
                    agent_id=solution_data.get('agent_id', 'unknown'),
                    domain=domain,
                    criteria=criteria
                )
                
                evaluated.append({
                    **solution_data,
                    'evaluation': {
                        'total': result.total_score,
                        'criteria': result.criteria_scores,
                        'passed': result.passed
                    },
                    'score': result.total_score
                })
            except Exception as e:
                logger.error(f"Evaluation failed for {solution_data.get('agent_id')}: {str(e)}")
                evaluated.append({
                    **solution_data,
                    'evaluation': {'total': 0.0, 'passed': False, 'error': str(e)},
                    'score': 0.0
                })
        
        return evaluated

    def _select_winner(self, evaluated_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best performing agent"""
        if not evaluated_results:
            return None
        
        # Filter successful evaluations
        valid_results = [r for r in evaluated_results if r.get('success', True)]
        if not valid_results:
            return None
        
        # Sort by score
        sorted_results = sorted(
            valid_results, 
            key=lambda x: x.get('score', 0), 
            reverse=True
        )
        
        winner = sorted_results[0]
        logger.info(f"Winner selected: {winner.get('agent_id')} with score {winner.get('score'):.2f}")
        
        return {
            'agent_id': winner.get('agent_id'),
            'score': winner.get('score'),
            'evaluation': winner.get('evaluation')
        }

    async def _record_learning(self, domain: str, result: CompetitionResult) -> None:
        """Record outcomes and patterns for future learning"""
        # Record competition outcome
        self.memory.record_competition_outcome(
            domain=domain,
            agent_count=len(result.agent_results),
            winner_agent=result.winner or "none",
            best_score=result.total_score,
            total_cost_usd=result.cost_estimate
        )
        
        # Learn from each agent's result
        for agent_result in result.agent_results:
            if agent_result.get('success') and agent_result.get('solution'):
                # Extract patterns from solutions
                solution = agent_result.get('solution', '')
                if solution.strip():
                    # Determine pattern type based on domain
                    pattern_type = self._infer_pattern_type(domain, solution)
                    
                    # Record successful pattern
                    self.memory.record_pattern(
                        domain=domain,
                        pattern_type=pattern_type,
                        description=f"Solution pattern with score {agent_result.get('score', 0):.2f}",
                        solution=solution[:500],  # Limit solution length
                        confidence=min(0.9, agent_result.get('score', 0.5) + 0.1)
                    )

    def _infer_pattern_type(self, domain: str, solution: str) -> str:
        """Infer pattern type from domain and solution content"""
        pattern_keywords = {
            'backend': ['security', 'database', 'api', 'performance', 'error'],
            'frontend_ui_ux': ['accessibility', 'responsive', 'design', 'component', 'layout'],
            'devops_cloud': ['deployment', 'monitoring', 'scaling', 'infrastructure', 'error'],
            'security': ['vulnerability', 'injection', 'auth', 'encryption', 'threat'],
            'data_ml': ['pipeline', 'model', 'training', 'data', 'feature'],
            'qa_testing': ['test', 'coverage', 'mock', 'assertion', 'validation'],
            'architecture': ['design', 'pattern', 'scalability', 'structure', 'modularity'],
            'agent_orchestration': ['coordination', 'tournament', 'evaluation', 'selection'],
            'code_refinement': ['optimization', 'refactor', 'improvement', 'bug', 'quality']
        }
        
        keywords = pattern_keywords.get(domain, ['general'])
        solution_lower = solution.lower()
        
        for keyword in keywords:
            if keyword in solution_lower:
                return keyword
        
        return 'general'

    def _estimate_cost(self, agent_count: int, timeout: int) -> float:
        """Estimate cost in USD for the competition"""
        # Rough estimate: $0.03 per 1000 tokens, assume 2000 tokens per agent timeout
        tokens_per_agent = 2000
        total_tokens = agent_count * tokens_per_agent * (timeout // 60)
        return (total_tokens / 1000) * 0.03

    def _create_dry_run_result(self, competition_id: str, config: CompetitionConfig) -> CompetitionResult:
        """Create a result for dry run mode"""
        return CompetitionResult(
            winner=None,
            total_score=0.0,
            agent_results=[{
                'agent_id': f'dummy_agent_{i+1}',
                'solution': '[DRY RUN - No solution]',
                'success': False
            } for i in range(config.agent_count)],
            competition_id=competition_id,
            execution_time=0.0,
            cost_estimate=0.0
        )

    def get_competition_history(self, domain: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get competition history, optionally filtered by domain"""
        if domain:
            return [
                h for h in self._competition_history 
                if h.get('domain') == domain
            ][:limit]
        return self._competition_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        return {
            'active_competitions': len(self.active_competitions),
            'total_competitions_run': len(self._competition_history),
            'domains_supported': len(self.domain_manager.list_domains()),
            'patterns_in_memory': sum(
                len(self.memory.get_lessons_for_domain(d)) 
                for d in [dm.id for dm in self.domain_manager.list_domains()]
            )
        }