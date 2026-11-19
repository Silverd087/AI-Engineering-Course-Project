from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Limits
from agent.nodes import route_after_agent, stop_node
from agent.state import AgentState
from agent.stop import StopReason

LIMITS = Limits(max_steps=5, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0)
START = 1000.0


def make_state(last_message, **overrides) -> AgentState:
    base = AgentState(
        messages=[HumanMessage(content="migrate the repo"), last_message],
        workspace="/tmp/ws",
        steps=1,
        cost_usd=0.01,
        recent_calls=[],
        started_at=START,
        stop_reason=None,
    )
    base.update(overrides)
    return base


def call(name: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "1"}])


def test_stop_when_stop_rule_fires():
    state = make_state(call("read_file", path="a.py"), steps=LIMITS.max_steps)
    assert route_after_agent(state, LIMITS, now=START) == "stop"


def test_approve_when_model_calls_write_tool():
    state = make_state(call("edit_file", path="a.py", old="x", new="y"))
    assert route_after_agent(state, LIMITS, now=START) == "approve"


def test_approve_for_open_pull_request():
    state = make_state(call("open_pull_request", branch="b", title="t", body="b"))
    assert route_after_agent(state, LIMITS, now=START) == "approve"


def test_tools_when_model_calls_read_tool():
    state = make_state(call("read_file", path="a.py"))
    assert route_after_agent(state, LIMITS, now=START) == "tools"


def test_tools_when_model_calls_run_tests():
    state = make_state(call("run_tests", target="tests/"))
    assert route_after_agent(state, LIMITS, now=START) == "tools"


def test_stop_when_model_calls_finish():
    state = make_state(call("finish", summary="ok", status="success"))
    assert route_after_agent(state, LIMITS, now=START) == "stop"


def test_stop_when_model_makes_no_tool_call():
    state = make_state(AIMessage(content="all done"))
    assert route_after_agent(state, LIMITS, now=START) == "stop"


def test_stop_wins_over_write_call():
    state = make_state(call("edit_file", path="a.py", old="x", new="y"), steps=LIMITS.max_steps)
    assert route_after_agent(state, LIMITS, now=START) == "stop"


def test_stop_node_records_the_reason():
    state = make_state(call("read_file", path="a.py"), cost_usd=LIMITS.max_cost_usd)
    result = stop_node(state, LIMITS, now=START)
    assert result["stop_reason"] == StopReason.BUDGET.value