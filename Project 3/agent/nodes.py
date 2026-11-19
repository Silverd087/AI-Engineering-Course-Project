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


ZERO_USAGE = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}


def final_model_record(state: AgentState, run_id: str) -> TraceRecord | None:
    """Trace record for the last model call, which ends the run and runs no tool.

    Without this record the step costs would not add up to the run total.
    """
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return None
    names = [c["name"] for c in last.tool_calls]
    if "finish" in names:
        label = "finish"
    elif names:
        label = "stopped"  # a limit was hit while tool calls were still pending
    else:
        label = "reply"    # the model answered without calling a tool
    usage = last.response_metadata.get("step_usage", dict(ZERO_USAGE))
    now = time.time()
    return TraceRecord(
        run_id=run_id,
        step=state["steps"],
        kind="model",
        tool=label,
        args={},
        ok=True,
        **usage_fields(usage),
        t_start=now,
        t_end=now,
    )


def last_ai_message(messages):
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def quit_model_record(state: AgentState, run_id: str, quit_call_id: str) -> TraceRecord | None:
    """Model record for a reply whose cost would otherwise be lost when the human quits.

    The reply's cost is attached to its first tool call. If the quit happens at a later call,
    the first call never runs and gets no record, so the cost is recorded here instead.
    """
    message = last_ai_message(state["messages"])
    if message is None or not message.tool_calls:
        return None
    if message.tool_calls[0]["id"] == quit_call_id:
        return None  # the quit call itself already carries this cost
    usage = message.response_metadata.get("step_usage", dict(ZERO_USAGE))
    now = time.time()
    return TraceRecord(
        run_id=run_id,
        step=state["steps"],
        kind="model",
        tool="quit",
        args={},
        ok=True,
        **usage_fields(usage),
        t_start=now,
        t_end=now,
    )


def agent_node(state: AgentState, model, settings) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    cost = cost_of(response, settings)
    usage = getattr(response, "usage_metadata", None) or {}
    # Keep this call's usage on the message, so the step that runs its tool calls can record it.
    response.response_metadata = {
        **(response.response_metadata or {}),
        "step_usage": {
            "tokens_in": usage.get("input_tokens", 0),
            "tokens_out": usage.get("output_tokens", 0),
            "cost_usd": cost,
        },
    }
    return {"messages": [response], "cost_usd": state["cost_usd"] + cost}


def step_usage(messages, call_id: str) -> dict:
    """Model usage to record on one tool step.

    One model call can request several tool calls. Its cost goes on the first of them
    only, so summing the step records never counts a model call twice. Any other call
    gets zeros.
    """
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            calls = message.tool_calls
            if calls and calls[0]["id"] == call_id:
                return message.response_metadata.get("step_usage", dict(ZERO_USAGE))
            return dict(ZERO_USAGE)
    return dict(ZERO_USAGE)


def usage_fields(usage: dict) -> dict:
    return {
        "tokens_in": usage["tokens_in"],
        "tokens_out": usage["tokens_out"],
        "cost_usd": usage["cost_usd"],
    }


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
                **usage_fields(step_usage(state["messages"], call["id"])),
                t_start=started,
                t_end=time.time(),
            )
        )

    return {
        "messages": messages,
        "steps": state["steps"] + len(messages),
        "recent_calls": state["recent_calls"] + signatures,
    }