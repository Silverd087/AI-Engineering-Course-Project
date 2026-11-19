import time

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.config import Limits, Settings
from agent.graph import build_graph
from agent.tools.base import ToolResult
from agent.trace import TraceWriter, read_trace

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


def edit_then_finish(n):
    if n == 1:
        return AIMessage(content="", tool_calls=[{"name": "edit_file", "args": EDIT_ARGS, "id": "e1"}])
    return AIMessage(content="", tool_calls=[{"name": "finish", "args": {"summary": "ok", "status": "success"}, "id": "f1"}])


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


def make_graph(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    tools = {"edit_file": lambda ws, a: ToolResult.success({"changed": True})}
    graph = build_graph(ScriptedModel(edit_then_finish), tools, SETTINGS, trace, run_id="r1", checkpointer=MemorySaver())
    return graph, tmp_path / "run.jsonl"


def test_rejected_write_is_traced_as_not_approved(tmp_path):
    graph, path = make_graph(tmp_path)
    graph.invoke(start_state(), CONFIG)
    graph.invoke(Command(resume="n"), CONFIG)
    record = read_trace(path)[0]
    assert record.tool == "edit_file"
    assert record.approved is False
    assert record.error_type == "rejected_by_human"


def test_quit_is_traced_as_not_approved(tmp_path):
    graph, path = make_graph(tmp_path)
    graph.invoke(start_state(), CONFIG)
    graph.invoke(Command(resume="q"), CONFIG)
    record = read_trace(path)[0]
    assert record.approved is False
    assert record.error_type == "user_quit"


def test_approved_write_is_traced_as_approved(tmp_path):
    graph, path = make_graph(tmp_path)
    graph.invoke(start_state(), CONFIG)
    graph.invoke(Command(resume="y"), CONFIG)
    edit = next(r for r in read_trace(path) if r.tool == "edit_file")
    assert edit.approved is True
    assert edit.ok is True