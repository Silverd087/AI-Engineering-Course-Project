"""Tests for the stop rule (A1) and its proof (A2)."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Limits
from agent.state import AgentState
from agent.stop import StopReason, check_stop

LIMITS = Limits(max_steps=5, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0)
START = 1000.0


def make_state(**overrides) -> AgentState:
    """A healthy mid-run state. Each test overrides only what it needs."""
    base = AgentState(
        messages=[
            HumanMessage(content="migrate the repo"),
            AIMessage(content="", tool_calls=[{"name": "read_file", "args": {"path": "a.py"}, "id": "1"}]),
        ],
        workspace="/tmp/ws",
        steps=1,
        cost_usd=0.01,
        recent_calls=['read_file:{"path": "a.py"}'],
        started_at=START,
        stop_reason=None,
    )
    base.update(overrides)
    return base


def finish_message() -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": "finish", "args": {"summary": "ok", "status": "success"}, "id": "9"}])


# --- Rule 1: done ----------------------------------------------------------

def test_done_when_model_calls_finish():
    state = make_state(messages=[HumanMessage(content="go"), finish_message()])
    assert check_stop(state, LIMITS, now=START) == StopReason.DONE


def test_done_when_model_makes_no_tool_call():
    state = make_state(messages=[HumanMessage(content="go"), AIMessage(content="I am finished.")])
    assert check_stop(state, LIMITS, now=START) == StopReason.DONE


def test_not_done_when_model_calls_a_normal_tool():
    assert check_stop(make_state(), LIMITS, now=START) is None


# --- Rule 2: max steps -----------------------------------------------------

def test_max_steps_at_limit():
    state = make_state(steps=LIMITS.max_steps)
    assert check_stop(state, LIMITS, now=START) == StopReason.MAX_STEPS


def test_max_steps_just_below_limit_continues():
    state = make_state(steps=LIMITS.max_steps - 1)
    assert check_stop(state, LIMITS, now=START) is None


# --- Rule 3: budget --------------------------------------------------------

def test_budget_at_limit():
    state = make_state(cost_usd=LIMITS.max_cost_usd)
    assert check_stop(state, LIMITS, now=START) == StopReason.BUDGET


def test_budget_just_below_limit_continues():
    state = make_state(cost_usd=LIMITS.max_cost_usd - 0.001)
    assert check_stop(state, LIMITS, now=START) is None


# --- Rule 4: looping -------------------------------------------------------

def test_looping_after_max_repeats_identical_calls():
    same = 'read_file:{"path": "a.py"}'
    state = make_state(recent_calls=[same] * LIMITS.max_repeats)
    assert check_stop(state, LIMITS, now=START) == StopReason.LOOPING


def test_not_looping_when_last_calls_differ():
    same = 'read_file:{"path": "a.py"}'
    other = 'read_file:{"path": "b.py"}'
    state = make_state(recent_calls=[same, same, other])
    assert check_stop(state, LIMITS, now=START) is None


def test_not_looping_with_fewer_calls_than_repeats():
    same = 'read_file:{"path": "a.py"}'
    state = make_state(recent_calls=[same] * (LIMITS.max_repeats - 1))
    assert check_stop(state, LIMITS, now=START) is None


# --- Rule 5: timeout -------------------------------------------------------

def test_timeout_at_limit():
    state = make_state()
    assert check_stop(state, LIMITS, now=START + LIMITS.task_timeout_s) == StopReason.TIMEOUT


def test_timeout_just_below_limit_continues():
    state = make_state()
    assert check_stop(state, LIMITS, now=START + LIMITS.task_timeout_s - 0.001) is None


# --- Order: done beats everything -------------------------------------------

def test_done_wins_over_max_steps_on_the_last_step():
    state = make_state(messages=[HumanMessage(content="go"), finish_message()], steps=LIMITS.max_steps)
    assert check_stop(state, LIMITS, now=START) == StopReason.DONE


# --- Edge: no messages at all -----------------------------------------------

def test_empty_messages_does_not_crash():
    state = make_state(messages=[])
    assert check_stop(state, LIMITS, now=START) is None


# --- Property test: the rule always decides, and never past the limits ------

@settings(max_examples=300, deadline=None)
@given(
    steps=st.integers(min_value=0, max_value=50),
    cost=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    elapsed=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    calls=st.lists(st.sampled_from(["a", "b"]), max_size=10),
)
def test_property_limits_are_always_enforced(steps, cost, elapsed, calls):
    state = make_state(steps=steps, cost_usd=cost, recent_calls=calls)
    result = check_stop(state, LIMITS, now=START + elapsed)

    over_a_limit = (
        steps >= LIMITS.max_steps
        or cost >= LIMITS.max_cost_usd
        or elapsed >= LIMITS.task_timeout_s
        or (len(calls) >= LIMITS.max_repeats and len(set(calls[-LIMITS.max_repeats:])) == 1)
    )
    if over_a_limit:
        assert result is not None, "a limit was passed but the loop kept going"
    else:
        assert result is None, "no limit was passed but the loop stopped"