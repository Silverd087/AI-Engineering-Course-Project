"""LangGraph state shared by every node."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    workspace: str              # absolute path of this run's sandbox copy (never chosen by the model)
    steps: int                  # tool calls executed so far
    cost_usd: float             # model cost so far
    recent_calls: list[str]     # signatures "tool:{sorted json args}" for the repetition rule
    started_at: float           # time.monotonic() at start, for the timeout rule
    stop_reason: str | None     # done | max_steps | budget | looping | timeout | user_quit
    finish_status: str | None   # success | gave_up, only set when the model called finish