"""Human checkpoint: the `approve` node (task A5).

TODO:
- approve_node(state): for each write call, interrupt({"tool", "args", "diff"})
  and resume with "y" | "n" | "q"
- "n" -> ToolMessage carrying ToolResult.failure(ErrorType.REJECTED_BY_HUMAN, ...)
- "q" -> stop_reason = "user_quit"
- ScriptedApprover for eval: approve_all / reject_nth / reject_outside_allowed
"""

"""Human checkpoint: the approve node (task A5)."""

import difflib

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from agent.nodes import WRITE_TOOLS, last_tool_calls
from agent.state import AgentState
from agent.stop import StopReason
from agent.tools.base import ErrorType, ToolResult


def describe(call: dict) -> dict:
    name, args = call["name"], call["args"]
    if name == "edit_file":
        diff = "".join(
            difflib.unified_diff(
                str(args.get("old", "")).splitlines(keepends=True),
                str(args.get("new", "")).splitlines(keepends=True),
                fromfile=str(args.get("path", "")),
                tofile=str(args.get("path", "")),
            )
        )
    else:
        diff = (
            f"branch: {args.get('branch', '')}\n"
            f"title: {args.get('title', '')}\n\n"
            f"{args.get('body', '')}"
        )
    return {"tool": name, "args": args, "diff": diff}


def approve_node(state: AgentState) -> dict:
    rejections = []
    for call in last_tool_calls(state["messages"]):
        if call["name"] not in WRITE_TOOLS:
            continue

        answer = interrupt(describe(call))  # the run pauses here until someone resumes it

        if answer == "q":
            return {"stop_reason": StopReason.USER_QUIT.value}
        if answer != "y":
            rejections.append(
                ToolMessage(
                    content=ToolResult.failure(
                        ErrorType.REJECTED_BY_HUMAN,
                        f"The human rejected this change to {call['name']}. Try a different approach, or call finish.",
                    ).to_json(),
                    tool_call_id=call["id"],
                )
            )
    return {"messages": rejections}