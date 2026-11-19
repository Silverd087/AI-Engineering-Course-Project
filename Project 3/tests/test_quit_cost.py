import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.config import Limits, Settings
from agent.graph import build_graph
from agent.nodes import quit_model_record
from agent.state import AgentState
from agent.tools.base import ToolResult
from agent.trace import TraceWriter, read_trace

LIMITS = Limits(max_steps=5, max_cost_usd=10.0, max_repeats=3, task_timeout_s=60.0)
SETTINGS = Settings(model="test", price_input_per_mtok=1.0, price_output_per_mtok=0.0, limits=LIMITS)
CONFIG = {"configurable": {"thread_id": "t1"}, "recursion_limit": 50}
ONE_MTOK = {"input_tokens": 1_000_000, "output_tokens": 0, "total_tokens": 1_000_000}


def state_with(message) -> AgentState:
    return {
        "messages": [HumanMessage(content="go"), message],
        "workspace": "/tmp/ws", "steps": 1, "cost_usd": 0.0, "recent_calls": [],
        "started_at": 0.0, "stop_reason": None, "finish_status": None,
    }


def test_no_quit_record_when_the_quit_call_is_the_first_call():
    message = AIMessage(
        content="",
        tool_calls=[{"name": "edit_file", "args": {}, "id": "e1"}],
        response_metadata={"step_usage": {"tokens_in": 1, "tokens_out": 0, "cost_usd": 1.0}},
    )
    assert quit_model_record(state_with(message), "r1", "e1") is None


def test_quit_record_carries_cost_when_the_first_call_never_ran():
    message = AIMessage(
        content="",
        tool_calls=[
            {"name": "read_file", "args": {}, "id": "r1"},
            {"name": "edit_file", "args": {}, "id": "e1"},
        ],
        response_metadata={"step_usage": {"tokens_in": 1_000_000, "tokens_out": 0, "cost_usd": 1.0}},
    )
    record = quit_model_record(state_with(message), "r1", "e1")
    assert (record.kind, record.tool, record.cost_usd) == ("model", "quit", 1.0)


def test_run_quit_at_a_later_write_keeps_the_total_reconciled(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    fake_read = lambda workspace, args: ToolResult.success({})

    class ScriptedModel:
        def invoke(self, messages):
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "read_file", "args": {"path": "a.py"}, "id": "r1"},
                    {"name": "edit_file", "args": {"path": "a.py", "old": "x", "new": "y"}, "id": "e1"},
                ],
                usage_metadata=ONE_MTOK,
            )

    graph = build_graph(ScriptedModel(), {"read_file": fake_read}, SETTINGS, trace, "r1", checkpointer=MemorySaver())
    graph.invoke({
        "messages": [HumanMessage(content="go")], "workspace": "/tmp/ws", "steps": 0, "cost_usd": 0.0,
        "recent_calls": [], "started_at": time.monotonic(), "stop_reason": None, "finish_status": None,
    }, CONFIG)
    graph.invoke(Command(resume="q"), CONFIG)

    records = read_trace(tmp_path / "run.jsonl")
    total = graph.get_state(CONFIG).values["cost_usd"]
    assert sum(r.cost_usd for r in records) == pytest.approx(total) == pytest.approx(1.0)
    assert [r.tool for r in records] == ["edit_file", "quit"]