import time

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.config import Limits, Settings
from agent.graph import build_graph
from agent.nodes import final_model_record
from agent.tools.base import ToolResult
from agent.trace import TraceWriter, read_trace
from eval.metrics import executed

LIMITS = Limits(max_steps=5, max_cost_usd=10.0, max_repeats=3, task_timeout_s=60.0)
SETTINGS = Settings(model="test", price_input_per_mtok=1.0, price_output_per_mtok=0.0, limits=LIMITS)
CONFIG = {"configurable": {"thread_id": "t1"}, "recursion_limit": 50}
ONE_MTOK = {"input_tokens": 1_000_000, "output_tokens": 0, "total_tokens": 1_000_000}


def state_with(last_message, steps=2):
    return {
        "messages": [HumanMessage(content="go"), last_message],
        "workspace": "/tmp/ws",
        "steps": steps,
        "cost_usd": 0.0,
        "recent_calls": [],
        "started_at": 0.0,
        "stop_reason": None,
        "finish_status": None,
    }


def ai(calls, cost=1.0):
    return AIMessage(
        content="",
        tool_calls=calls,
        response_metadata={"step_usage": {"tokens_in": 1_000_000, "tokens_out": 0, "cost_usd": cost}},
    )


def test_final_finish_call_is_recorded_as_model_step():
    record = final_model_record(state_with(ai([{"name": "finish", "args": {}, "id": "f1"}])), "r1")
    assert (record.kind, record.tool, record.cost_usd) == ("model", "finish", 1.0)


def test_final_plain_reply_is_recorded_as_reply():
    record = final_model_record(state_with(AIMessage(content="all done")), "r1")
    assert (record.kind, record.tool) == ("model", "reply")


def test_limit_hit_with_pending_calls_is_recorded_as_stopped():
    record = final_model_record(state_with(ai([{"name": "read_file", "args": {}, "id": "c1"}])), "r1")
    assert record.tool == "stopped"


def test_no_record_when_last_message_is_not_a_model_reply():
    assert final_model_record({"messages": [HumanMessage(content="go")], "steps": 0}, "r1") is None


def test_metrics_ignore_model_records(tmp_path):
    tool = TraceWriter(tmp_path / "run.jsonl")
    fake_read = lambda workspace, args: ToolResult.success({})

    class ScriptedModel:
        def __init__(self):
            self.replies = [
                AIMessage(content="", tool_calls=[{"name": "read_file", "args": {"path": "a.py"}, "id": "r1"}],
                          usage_metadata=ONE_MTOK),
                AIMessage(content="", tool_calls=[{"name": "finish", "args": {"summary": "ok", "status": "success"}, "id": "f1"}],
                          usage_metadata=ONE_MTOK),
            ]

        def invoke(self, messages):
            return self.replies.pop(0)

    graph = build_graph(ScriptedModel(), {"read_file": fake_read}, SETTINGS, tool, "r1", checkpointer=MemorySaver())
    final = graph.invoke({
        "messages": [HumanMessage(content="go")], "workspace": "/tmp/ws", "steps": 0, "cost_usd": 0.0,
        "recent_calls": [], "started_at": time.monotonic(), "stop_reason": None, "finish_status": None,
    }, CONFIG)

    records = read_trace(tmp_path / "run.jsonl")
    assert [r.kind for r in records] == ["tool", "model"]
    assert sum(r.cost_usd for r in records) == final["cost_usd"] == 2.0
    assert [r.tool for r in executed(records)] == ["read_file"]