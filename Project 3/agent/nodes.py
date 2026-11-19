"""Graph nodes (task A4, A6, A7)."""

import json
import logging
import time

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from agent.config import Limits
from agent.llm import cost_of
from agent.prompts import SYSTEM_PROMPT, UNTRUSTED_CLOSE, UNTRUSTED_OPEN
from agent.state import AgentState
from agent.stop import check_stop
from agent.tools.base import ErrorType, ToolResult
from agent.trace import TraceRecord, TraceWriter

WRITE_TOOLS = {"edit_file", "open_pull_request"}
VALID_FINISH_STATUSES = ("success", "gave_up")

logger = logging.getLogger(__name__)


def last_tool_calls(messages) -> list:
    # The most recent AI message's tool calls. Approval adds ToolMessages after
    # it, so messages[-1] is no longer always the AI message.
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message.tool_calls
    return []


def route_after_agent(state: AgentState, limits: Limits, now: float) -> str:
    if check_stop(state, limits, now) is not None:
        return "stop"

    last = state["messages"][-1]
    for call in getattr(last, "tool_calls", None) or []:
        if call["name"] in WRITE_TOOLS:
            return "approve"

    return "tools"


def route_after_approve(state: AgentState) -> str:
    if state.get("stop_reason"):
        return "end"
    answered = {m.tool_call_id for m in state["messages"] if isinstance(m, ToolMessage)}
    pending = [c for c in last_tool_calls(state["messages"]) if c["id"] not in answered]
    return "tools" if pending else "agent"


def finish_status_of(messages) -> str | None:
    # Only a finish call carries a status. Anything other than "success" counts
    # as "gave_up", so an unclear or missing status is never a pass.
    for call in last_tool_calls(messages):
        if call["name"] == "finish":
            status = call["args"].get("status")
            return status if status in VALID_FINISH_STATUSES else "gave_up"
    return None


def stop_node(state: AgentState, limits: Limits, now: float) -> dict:
    reason = check_stop(state, limits, now)
    return {
        "stop_reason": reason.value if reason else None,
        "finish_status": finish_status_of(state["messages"]),
    }


def agent_node(state: AgentState, model, settings) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    cost = cost_of(response, settings)
    return {"messages": [response], "cost_usd": state["cost_usd"] + cost}


def signature(name: str, args: dict) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True)}"


def tools_node(state: AgentState, tools: dict, trace: TraceWriter, run_id: str) -> dict:
    calls = last_tool_calls(state["messages"])
    answered = {m.tool_call_id for m in state["messages"] if isinstance(m, ToolMessage)}
    messages = []
    signatures = []

    for call in calls:
        if call["id"] in answered:
            continue  # already rejected by the human, so don't run it
        name, args = call["name"], call["args"]
        started = time.time()

        tool = tools.get(name)
        if tool is None:
            result = ToolResult.failure(
                ErrorType.NOT_FOUND,
                f"There is no tool named '{name}'. Use one of the available tools.",
            )
        else:
            try:
                result = tool(state["workspace"], args)
            except Exception:
                logger.exception("tool %s crashed", name)
                result = ToolResult.failure(
                    ErrorType.INTERNAL,
                    f"The '{name}' tool failed unexpectedly. Try a different approach or another tool.",
                )

        output = result.to_json()
        messages.append(
            ToolMessage(content=f"{UNTRUSTED_OPEN}\n{output}\n{UNTRUSTED_CLOSE}", tool_call_id=call["id"])
        )
        signatures.append(signature(name, args))
        trace.write(
            TraceRecord(
                run_id=run_id,
                step=state["steps"] + len(messages),
                tool=name,
                args=args,
                ok=result.ok,
                error_type=result.error_type,
                output_preview=output[:500],
                approved=True if name in WRITE_TOOLS else None,
                t_start=started,
                t_end=time.time(),
            )
        )

    return {
        "messages": messages,
        "steps": state["steps"] + len(messages),
        "recent_calls": state["recent_calls"] + signatures,
    }