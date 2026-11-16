"""Stop rule. WRITE THIS FIRST (README section 2, task A1).

check_stop() is called by the router after every model turn. It returns the
reason to stop, or None to continue. Rules, in order:
  1. done      - the model called `finish` (or made no tool call)
  2. max_steps - state["steps"] >= limits.max_steps
  3. budget    - state["cost_usd"] >= limits.max_cost_usd
  4. looping   - the last `limits.max_repeats` entries of recent_calls are identical
  5. timeout   - now - state["started_at"] >= limits.task_timeout_s
"""

from __future__ import annotations

from enum import StrEnum

from agent.config import Limits
from agent.state import AgentState


class StopReason(StrEnum):
    DONE = "done"
    MAX_STEPS = "max_steps"
    BUDGET = "budget"
    LOOPING = "looping"
    TIMEOUT = "timeout"
    USER_QUIT = "user_quit"


def check_stop(state: AgentState, limits: Limits, now: float) -> StopReason | None:
    # Rule 1: done. The model called `finish`, or made no tool call at all.
    messages = state["messages"]
    last = messages[-1] if messages else None
    tool_calls = getattr(last, "tool_calls", None) or []
    if last is not None and (not tool_calls or any(c["name"] == "finish" for c in tool_calls)):
        return StopReason.DONE

    # Rule 2: step limit. Too many tool calls have run.
    if state["steps"] >= limits.max_steps:
        return StopReason.MAX_STEPS

    # Rule 3: budget. Too much money has been spent on model calls.
    if state["cost_usd"] >= limits.max_cost_usd:
        return StopReason.BUDGET

    # Rule 4: looping. The last N calls are all identical.
    n = limits.max_repeats
    recent = state["recent_calls"]
    if len(recent) >= n and len(set(recent[-n:])) == 1:
        return StopReason.LOOPING

    # Rule 5: timeout. The task has run for too long.
    if now - state["started_at"] >= limits.task_timeout_s:
        return StopReason.TIMEOUT

    # No rule matched, so the loop continues.
    return None