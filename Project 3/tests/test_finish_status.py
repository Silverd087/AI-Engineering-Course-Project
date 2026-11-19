import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Limits
from agent.nodes import stop_node
from agent.state import AgentState

LIMITS = Limits(max_steps=5, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0)


def state_with(last_message, **overrides):
    base = AgentState(
        messages=[HumanMessage(content="migrate the repo"), last_message],
        workspace="/tmp/ws",
        steps=1,
        cost_usd=0.0,
        recent_calls=[],
        started_at=0.0,
        stop_reason=None,
        finish_status=None,
    )
    base.update(overrides)
    return base


def finish_call(**args):
    return AIMessage(content="", tool_calls=[{"name": "finish", "args": args, "id": "f1"}])


def test_success_is_recorded():
    result = stop_node(state_with(finish_call(summary="ok", status="success")), LIMITS, now=0.0)
    assert result == {"stop_reason": "done", "finish_status": "success"}


def test_gave_up_is_recorded():
    result = stop_node(state_with(finish_call(summary="stuck", status="gave_up")), LIMITS, now=0.0)
    assert result == {"stop_reason": "done", "finish_status": "gave_up"}


@pytest.mark.parametrize("args", [{"summary": "x", "status": "maybe"}, {"summary": "x"}])
def test_unclear_status_counts_as_gave_up(args):
    result = stop_node(state_with(finish_call(**args)), LIMITS, now=0.0)
    assert result["finish_status"] == "gave_up"


def test_text_only_reply_has_no_status():
    # The model stopped without calling finish. The run ends as done, but it is not a success.
    result = stop_node(state_with(AIMessage(content="All done.")), LIMITS, now=0.0)
    assert result == {"stop_reason": "done", "finish_status": None}


def test_budget_stop_has_no_status():
    result = stop_node(state_with(AIMessage(content="", tool_calls=[{"name": "read_file", "args": {"path": "a.py"}, "id": "1"}]),
                                  cost_usd=LIMITS.max_cost_usd),
                       LIMITS, now=0.0)
    assert result == {"stop_reason": "budget", "finish_status": None}