import importlib
import subprocess
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes import tools_node
from agent.state import AgentState
from agent.tools.base import ErrorType
from agent.trace import TraceWriter

run_tests_module = importlib.import_module("agent.tools.run_tests")
ERRORS_MD = Path(__file__).resolve().parents[1] / "errors.md"


def make_state(calls) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content="go"), AIMessage(content="", tool_calls=calls)],
        workspace="/tmp/ws",
        steps=0,
        cost_usd=0.0,
        recent_calls=[],
        started_at=0.0,
        stop_reason=None,
    )


def test_crashing_tool_becomes_internal_error_without_leaking_details(tmp_path):
    def broken(workspace, args):
        raise RuntimeError("secret detail from inside the tool")

    trace = TraceWriter(tmp_path / "run.jsonl")
    state = make_state([{"name": "broken", "args": {}, "id": "c1"}])
    result = tools_node(state, {"broken": broken}, trace, run_id="r1")

    content = result["messages"][0].content
    assert '"error_type": "internal_error"' in content
    assert "failed unexpectedly" in content
    assert "secret detail" not in content


def test_run_tests_timeout_becomes_timeout_error(tmp_path, monkeypatch):
    def too_slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=1)

    monkeypatch.setattr(run_tests_module.subprocess, "run", too_slow)
    result = run_tests_module.run_tests(str(tmp_path), {})

    assert result.error_type == ErrorType.TIMEOUT
    assert "took longer than" in result.message


def test_every_error_type_is_documented_in_errors_md():
    text = ERRORS_MD.read_text(encoding="utf-8")
    missing = [e.value for e in ErrorType if f"`{e.value}`" not in text]
    assert missing == []