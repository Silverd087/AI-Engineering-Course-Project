"""Graph nodes (task A4).

TODO:
- agent_node(state): call the model, add its cost to state["cost_usd"]
- tools_node(state): run validated tool calls, wrap outputs in UNTRUSTED tags,
  write one TraceRecord per call, increment state["steps"]
- route_after_agent(state): check check_stop() first, then return
  "approve" (write call) | "tools" (read/exec call) | END
"""
import json
import time

from agent.config import Limits
from agent.state import AgentState
from agent.stop import StopReason, check_stop
from agent.llm import cost_of
from agent.prompts import UNTRUSTED_CLOSE, UNTRUSTED_OPEN
from agent.tools.base import ErrorType, ToolResult
from agent.trace import TraceRecord, TraceWriter

from langchain_core.messages import AIMessage, ToolMessage


WRITE_TOOLS = {"edit_file", "open_pull_request"}


def last_tool_calls(messages) -> list:
    # The most recent AI message's tool calls. Approval adds ToolMessages after
    # it, so we can't just look at messages[-1] any more.
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message.tool_calls
    return []


def route_after_approve(state: AgentState) -> str:
    if state.get("stop_reason"):
        return "end"
    answered = {m.tool_call_id for m in state["messages"] if isinstance(m, ToolMessage)}
    pending = [c for c in last_tool_calls(state["messages"]) if c["id"] not in answered]
    return "tools" if pending else "agent"

def agent_node(state: AgentState, model, settings) -> dict:
    response = model.invoke(state["messages"])
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
            result = tool(state["workspace"], args)

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
                t_start=started,
                t_end=time.time(),
            )
        )

    return {
        "messages": messages,
        "steps": state["steps"] + len(messages),
        "recent_calls": state["recent_calls"] + signatures,
    }

def route_after_agent(state: AgentState, limits: Limits, now: float) -> str:
    if check_stop(state, limits, now) is not None:
        return "stop"

    last = state["messages"][-1]
    for call in getattr(last, "tool_calls", None) or []:
        if call["name"] in WRITE_TOOLS:
            return "approve"

    return "tools"


def stop_node(state: AgentState, limits: Limits, now: float) -> dict:
    reason = check_stop(state, limits, now)
    return {"stop_reason": reason.value if reason else None}