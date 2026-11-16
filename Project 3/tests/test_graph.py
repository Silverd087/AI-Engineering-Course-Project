import time
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Limits, Settings
from agent.graph import build_graph
from agent.stop import StopReason
from agent.tools.base import ToolResult
from agent.trace import TraceWriter

LIMITS = Limits(max_steps=5, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0)
SETTINGS = Settings(model="test", price_input_per_mtok=1.0, price_output_per_mtok=0.0, limits=LIMITS)


class ScriptedModel:
    """Replies with whatever make_reply(call_number) returns. Never calls a real API."""

    def __init__(self, make_reply):
        self.make_reply = make_reply
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.make_reply(self.calls)


def call(name, args, usage=None, call_id="1"):
    kwargs = {"usage_metadata": usage} if usage else {}
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}], **kwargs)


def fake_read(workspace, args):
    return ToolResult.success({"text": f"contents of {args['path']}"})


def run(model, tools, tmp_path, settings=SETTINGS):
    trace = TraceWriter(tmp_path / "run.jsonl")
    graph = build_graph(model, tools, settings, trace, run_id="test")
    state = {
        "messages": [HumanMessage(content="migrate the repo")],
        "workspace": "/tmp/ws",
        "steps": 0,
        "cost_usd": 0.0,
        "recent_calls": [],
        "started_at": time.monotonic(),
        "stop_reason": None,
    }
    return graph.invoke(state, config={"recursion_limit": 50})


def test_model_that_never_finishes_is_stopped_by_max_steps(tmp_path):
    model = ScriptedModel(lambda n: call("read_file", {"path": f"file_{n}.py"}, call_id=str(n)))
    result = run(model, {"read_file": fake_read}, tmp_path)
    assert result["stop_reason"] == StopReason.MAX_STEPS
    assert result["steps"] == LIMITS.max_steps


def test_model_repeating_the_same_call_is_stopped_as_looping(tmp_path):
    model = ScriptedModel(lambda n: call("read_file", {"path": "a.py"}, call_id=str(n)))
    result = run(model, {"read_file": fake_read}, tmp_path)
    assert result["stop_reason"] == StopReason.LOOPING


def test_model_calling_finish_ends_as_done(tmp_path):
    model = ScriptedModel(lambda n: call("finish", {"summary": "ok", "status": "success"}))
    result = run(model, {"read_file": fake_read}, tmp_path)
    assert result["stop_reason"] == StopReason.DONE
    assert result["steps"] == 0


def test_model_over_budget_is_stopped_as_budget(tmp_path):
    usage = {"input_tokens": 1_000_000, "output_tokens": 0, "total_tokens": 1_000_000}
    model = ScriptedModel(lambda n: call("read_file", {"path": f"file_{n}.py"}, usage=usage, call_id=str(n)))
    result = run(model, {"read_file": fake_read}, tmp_path)
    assert result["stop_reason"] == StopReason.BUDGET


def test_write_call_is_not_run_without_approval(tmp_path):
    ran = []

    def fake_edit(workspace, args):
        ran.append(args)
        return ToolResult.success({"changed": True})

    model = ScriptedModel(lambda n: call("edit_file", {"path": "a.py", "old": "x", "new": "y"}))
    result = run(model, {"edit_file": fake_edit}, tmp_path)
    assert ran == []
    assert result["stop_reason"] is None