"""Run a deterministic simulated competition from Python."""

import asyncio
from pathlib import Path
from tempfile import gettempdir

from openorchestra import CompetitionConfig, CompetitionOrchestrator
from openorchestra.memory import CompetitionMemory


async def main() -> None:
    memory = CompetitionMemory(db_path=str(Path(gettempdir()) / "openorchestra-example.db"))
    orchestrator = CompetitionOrchestrator(memory=memory)
    result = await orchestrator.run_competition(
        CompetitionConfig(
            domain="backend",
            task_description="Create a safe user endpoint",
            agent_count=3,
            simulate=True,
            record_memory=False,
        )
    )

    print(f"Competition: {result.competition_id}")
    print(f"Winner: {result.winner}")
    print(f"Score: {result.total_score:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
