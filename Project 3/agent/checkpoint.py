"""Human checkpoint: the approve node (task A5, A6)."""

import difflib
import time

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from agent.nodes import WRITE_TOOLS, last_tool_calls, quit_model_record, step_usage, usage_fields
from agent.state import AgentState
from agent.stop import StopReason
from agent.tools.base import ErrorType, ToolResult
from agent.trace import TraceRecord


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


def approve_node(state: AgentState, trace, run_id: str) -> dict:
    rejections = []
    for call in last_tool_calls(state["messages"]):
        if call["name"] not in WRITE_TOOLS:
            continue

        answer = interrupt(describe(call))  # the run pauses here until someone resumes it

        if answer == "y":
            continue

        # Record the human's decision in the trace, for both rejections and quits.
        now = time.time()
        error_type = "user_quit" if answer == "q" else ErrorType.REJECTED_BY_HUMAN.value
        trace.write(
            TraceRecord(
                run_id=run_id,
                step=state["steps"],
                tool=call["name"],
                args=call["args"],
                ok=False,
                error_type=error_type,
                output_preview=f"Human answered '{answer}'",
                approved=False,
                **usage_fields(step_usage(state["messages"], call["id"])),
                t_start=now,
                t_end=now,
            )
        )

        if answer == "q":
            quit_record = quit_model_record(state, run_id, call["id"])
            if quit_record is not None:
                trace.write(quit_record)
            return {"stop_reason": StopReason.USER_QUIT.value}

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