import time
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.config import Limits, Settings
from agent.graph import build_graph
from agent.stop import StopReason
from agent.tools.base import ToolResult
from agent.trace import TraceWriter

LIMITS = Limits(max_steps=5, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0)
SETTINGS = Settings(model="test", price_input_per_mtok=1.0, price_output_per_mtok=0.0, limits=LIMITS)
CONFIG = {"configurable": {"thread_id": "t1"}, "recursion_limit": 50}
EDIT_ARGS = {"path": "a.py", "old": "x = 1", "new": "x = 2"}


class ScriptedModel:
    def __init__(self, make_reply):
        self.make_reply = make_reply
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.make_reply(self.calls)


def call(name, args, call_id="1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def edit_then_finish(n):
    if n == 1:
        return call("edit_file", EDIT_ARGS, call_id="e1")
    return call("finish", {"summary": "ok", "status": "success"}, call_id="f1")


def start_state():
    return {
        "messages": [HumanMessage(content="migrate the repo")],
        "workspace": "/tmp/ws",
        "steps": 0,
        "cost_usd": 0.0,
        "recent_calls": [],
        "started_at": time.monotonic(),
        "stop_reason": None,
    }


def make_graph(model, tools, tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    return build_graph(model, tools, SETTINGS, trace, run_id="test", checkpointer=MemorySaver())


def test_run_pauses_before_a_write(tmp_path):
    ran = []
    model = ScriptedModel(edit_then_finish)
    graph = make_graph(model, {"edit_file": lambda ws, a: ran.append(a) or ToolResult.success({})}, tmp_path)
    paused = graph.invoke(start_state(), CONFIG)
    assert "__interrupt__" in paused
    assert ran == []


def test_approved_write_runs(tmp_path):
    ran = []
    model = ScriptedModel(edit_then_finish)
    graph = make_graph(model, {"edit_file": lambda ws, a: ran.append(a) or ToolResult.success({})}, tmp_path)
    graph.invoke(start_state(), CONFIG)
    final = graph.invoke(Command(resume="y"), CONFIG)
    assert ran == [EDIT_ARGS]
    assert final["stop_reason"] == StopReason.DONE


def test_rejected_write_does_not_run_and_model_is_told(tmp_path):
    ran = []
    model = ScriptedModel(edit_then_finish)
    graph = make_graph(model, {"edit_file": lambda ws, a: ran.append(a) or ToolResult.success({})}, tmp_path)
    graph.invoke(start_state(), CONFIG)
    final = graph.invoke(Command(resume="n"), CONFIG)
    assert ran == []
    assert model.calls == 2
    assert final["stop_reason"] == StopReason.DONE


def test_quit_ends_the_run_without_running_the_write(tmp_path):
    ran = []
    model = ScriptedModel(edit_then_finish)
    graph = make_graph(model, {"edit_file": lambda ws, a: ran.append(a) or ToolResult.success({})}, tmp_path)
    graph.invoke(start_state(), CONFIG)
    final = graph.invoke(Command(resume="q"), CONFIG)
    assert ran == []
    assert final["stop_reason"] == StopReason.USER_QUIT