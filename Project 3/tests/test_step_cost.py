import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Settings
from agent.nodes import agent_node, step_usage, tools_node
from agent.state import AgentState
from agent.tools.base import ToolResult
from agent.trace import TraceWriter, read_trace

SETTINGS = Settings(model="test-model", price_input_per_mtok=2.0, price_output_per_mtok=8.0)
USAGE = {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.02}


class FakeModel:
    def __init__(self, reply):
        self.reply = reply

    def invoke(self, messages):
        return self.reply


def make_state(calls, messages=None) -> AgentState:
    return AgentState(
        messages=messages or [HumanMessage(content="go"), AIMessage(content="", tool_calls=calls, response_metadata={"step_usage": USAGE})],
        workspace="/tmp/ws",
        steps=0,
        cost_usd=0.0,
        recent_calls=[],
        started_at=0.0,
        stop_reason=None,
    )


def fake_read(workspace, args):
    return ToolResult.success({"path": args["path"]})


def test_first_tool_call_carries_the_model_cost(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    calls = [
        {"name": "read_file", "args": {"path": "a.py"}, "id": "c1"},
        {"name": "read_file", "args": {"path": "b.py"}, "id": "c2"},
    ]
    tools_node(make_state(calls), {"read_file": fake_read}, trace, run_id="r1")

    first, second = read_trace(tmp_path / "run.jsonl")
    assert (first.tokens_in, first.tokens_out, first.cost_usd) == (100, 50, pytest.approx(0.02))
    assert (second.tokens_in, second.tokens_out, second.cost_usd) == (0, 0, 0.0)


def test_agent_node_keeps_this_calls_usage_on_the_reply():
    reply = AIMessage(
        content="",
        tool_calls=[{"name": "read_file", "args": {"path": "a.py"}, "id": "c1"}],
        usage_metadata={"input_tokens": 1_000_000, "output_tokens": 500_000, "total_tokens": 1_500_000},
    )
    agent_node(AgentState(
        messages=[HumanMessage(content="go")], workspace="/tmp/ws", steps=0, cost_usd=0.0,
        recent_calls=[], started_at=0.0, stop_reason=None,
    ), FakeModel(reply), SETTINGS)

    usage = reply.response_metadata["step_usage"]
    assert (usage["tokens_in"], usage["tokens_out"]) == (1_000_000, 500_000)
    assert usage["cost_usd"] == pytest.approx(2.0 + 4.0)


def test_unknown_call_has_no_usage():
    messages = [HumanMessage(content="go"), AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "c1"}])]
    assert step_usage(messages, "not-a-call") == {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    assert step_usage([HumanMessage(content="go")], "c1") == {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}