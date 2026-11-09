"""Tests for external integrations."""

import json
import os
import stat
from pathlib import Path

from openorchestra.integrations.agent_arena_bridge import AgentArenaBridge
from openorchestra.integrations.autodev_adapter import AutoDevAdapter
from openorchestra.integrations.opencode_adapter import OpenCodeAdapter


def make_fake_opencode(tmp_path: Path, text: str = "live solution") -> Path:
    script = tmp_path / "fake-opencode"
    script.write_text(
        f"""#!{os.sys.executable}
import json
import sys

if "--version" in sys.argv:
    print("fake-opencode 1.0")
    sys.exit(0)

if "--auto" not in sys.argv:
    sys.stderr.write("missing --auto")
    sys.exit(3)

print(json.dumps({{"type": "text", "text": {text!r}}}))
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_missing_binary_is_detected(tmp_path: Path) -> None:
    adapter = OpenCodeAdapter(opencode_path=str(tmp_path / "missing"), simulate=None)
    assert adapter.available is False
    assert adapter.simulate is True


async def test_simulated_execution() -> None:
    adapter = OpenCodeAdapter(simulate=True)
    result = await adapter.execute_skill_task("build a page", "agent_1", timeout=5)

    assert result["success"] is True
    assert "agent_1" in result["solution"]
    assert result["agent_id"] == "agent_1"


async def test_live_execution_uses_subprocess(tmp_path: Path) -> None:
    script = make_fake_opencode(tmp_path)
    adapter = OpenCodeAdapter(opencode_path=str(script), simulate=False)

    result = await adapter.execute_skill_task("build a page", "agent_1", timeout=10)

    assert adapter.available is True
    assert result["success"] is True
    assert result["solution"] == "live solution"


async def test_live_missing_binary_returns_failure(tmp_path: Path) -> None:
    adapter = OpenCodeAdapter(opencode_path=str(tmp_path / "missing"), simulate=False)

    result = await adapter.execute_skill_task("task", "agent_1", timeout=5)

    assert result["success"] is False
    assert result["solution"] == ""
    assert "Unable to start OpenCode" in result["error"]


async def test_live_execution_reports_nonzero_exit(tmp_path: Path) -> None:
    script = tmp_path / "failing-opencode"
    script.write_text(
        f"#!{os.sys.executable}\nimport sys\n"
        "if '--version' in sys.argv:\n    sys.exit(0)\n"
        "sys.stderr.write('boom')\n    \nsys.exit(2)\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    adapter = OpenCodeAdapter(opencode_path=str(script), simulate=False)

    result = await adapter.execute_skill_task("task", timeout=10)
    assert result["success"] is False
    assert result["solution"] == ""


async def test_run_parallel_tasks_returns_all_results() -> None:
    adapter = OpenCodeAdapter(simulate=True)
    results = await adapter.run_parallel_tasks(["a", "b"], agent_count=3, timeout=5)

    assert len(results) == 3
    assert [item["agent_id"] for item in results] == ["agent_1", "agent_2", "agent_3"]
    assert all(item["success"] for item in results)


def test_parse_output_collects_nested_json_text() -> None:
    output = "\n".join(
        [
            json.dumps({"text": "direct"}),
            json.dumps({"nested": {"text": "nested"}}),
            json.dumps([{"text": "listed"}]),
            json.dumps("plain-json-string"),
            "raw line",
        ]
    )

    assert OpenCodeAdapter._parse_output(output) == (
        "direct\nnested\nlisted\nplain-json-string\nraw line"
    )


def test_collect_text_ignores_non_text_scalars() -> None:
    chunks: list[str] = []
    OpenCodeAdapter._collect_text(42, chunks)
    OpenCodeAdapter._collect_text({"value": 42, "empty": ""}, chunks)

    assert chunks == []


def test_skill_detection_is_delegated() -> None:
    skills = OpenCodeAdapter(simulate=True).detect_skills()
    assert isinstance(skills, list)
    assert "clean-code" in skills


def test_skill_info_lookup() -> None:
    adapter = OpenCodeAdapter(simulate=True)
    assert adapter.get_skill_info("clean-code")["name"] == "Clean Code Principles"
    assert adapter.get_skill_info("missing") is None


def test_autodev_fallback_is_explicit() -> None:
    adapter = AutoDevAdapter()
    adapter._available = False
    result = adapter.run_tournament("task", "backend", 2)

    assert result["success"] is False
    assert result["winner"] is None
    assert "not available" in result["error"]


async def test_autodev_async_method() -> None:
    adapter = AutoDevAdapter()
    adapter._available = False
    result = await adapter.run_tournament_async("task", "backend", 1)
    assert result["success"] is False


def test_autodev_available_returns_winner() -> None:
    adapter = AutoDevAdapter()
    adapter._available = True
    result = adapter.run_tournament("task", "backend", 2)

    assert result["success"] is True
    assert result["winner"] == "winner_agent_0"


def test_arena_fallback_picks_longer_solution() -> None:
    bridge = AgentArenaBridge()
    bridge._available = False
    result = bridge.evaluate_comparison("short", "a much longer solution")

    assert result["winner"] == "agent_b"
    assert result["agent_b_score"] > result["agent_a_score"]


def test_arena_available_returns_comparison() -> None:
    bridge = AgentArenaBridge()
    bridge._available = True
    result = bridge.evaluate_comparison("a", "b")

    assert result["success"] is True
    assert result["winner"] == "agent_b"
