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
    raise NotImplementedError("A1: implement the stop rule")
