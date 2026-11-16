from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes import signature, tools_node
from agent.state import AgentState
from agent.tools.base import ErrorType, ToolResult
from agent.trace import TraceWriter, read_trace


def make_state(calls, **overrides) -> AgentState:
    base = AgentState(
        messages=[HumanMessage(content="go"), AIMessage(content="", tool_calls=calls)],
        workspace="/tmp/ws",
        steps=0,
        cost_usd=0.0,
        recent_calls=[],
        started_at=0.0,
        stop_reason=None,
    )
    base.update(overrides)
    return base


def fake_read(workspace, args):
    return ToolResult.success({"workspace": workspace, "path": args["path"]})


def test_runs_tool_and_wraps_output(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    state = make_state([{"name": "read_file", "args": {"path": "a.py"}, "id": "c1"}])
    result = tools_node(state, {"read_file": fake_read}, trace, run_id="r1")

    msg = result["messages"][0]
    assert msg.tool_call_id == "c1"
    assert msg.content.startswith("<untrusted_tool_output>")
    assert '"path": "a.py"' in msg.content
    assert '"workspace": "/tmp/ws"' in msg.content


def test_counts_steps_and_records_signatures(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    state = make_state([
        {"name": "read_file", "args": {"path": "a.py"}, "id": "c1"},
        {"name": "read_file", "args": {"path": "b.py"}, "id": "c2"},
    ], steps=3)
    result = tools_node(state, {"read_file": fake_read}, trace, run_id="r1")

    assert result["steps"] == 5
    assert result["recent_calls"] == [
        signature("read_file", {"path": "a.py"}),
        signature("read_file", {"path": "b.py"}),
    ]


def test_unknown_tool_returns_not_found(tmp_path):
    trace = TraceWriter(tmp_path / "run.jsonl")
    state = make_state([{"name": "delete_everything", "args": {}, "id": "c1"}])
    result = tools_node(state, {}, trace, run_id="r1")

    assert '"error_type": "not_found"' in result["messages"][0].content


def test_writes_one_trace_record_per_call(tmp_path):
    path = tmp_path / "run.jsonl"
    trace = TraceWriter(path)
    state = make_state([
        {"name": "read_file", "args": {"path": "a.py"}, "id": "c1"},
        {"name": "read_file", "args": {"path": "b.py"}, "id": "c2"},
    ])
    tools_node(state, {"read_file": fake_read}, trace, run_id="r1")

    records = read_trace(path)
    assert [r.step for r in records] == [1, 2]
    assert all(r.ok and r.tool == "read_file" for r in records)


def test_failed_tool_is_traced_as_failure(tmp_path):
    def broken(workspace, args):
        return ToolResult.failure(ErrorType.NOT_FOUND, "File 'x.py' not found.")

    path = tmp_path / "run.jsonl"
    trace = TraceWriter(path)
    state = make_state([{"name": "read_file", "args": {"path": "x.py"}, "id": "c1"}])
    tools_node(state, {"read_file": broken}, trace, run_id="r1")

    record = read_trace(path)[0]
    assert record.ok is False
    assert record.error_type == "not_found"