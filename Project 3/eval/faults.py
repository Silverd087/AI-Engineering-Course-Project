"""Fault injection (task C2).

TODO: wrap a tool so that its Nth call returns a failure instead of running:
  down -> TOOL_UNAVAILABLE, timeout -> TIMEOUT, empty -> success with empty result,
  bad_output -> garbled result, server_error -> TOOL_UNAVAILABLE ("PR API returned 500").
Driven by Scenario.faults.
"""

"""Fault injection (task C2). Makes a tool fail on a chosen call, instead of running it.

Driven by Scenario.faults. On a faulted call the real tool does not run, so the workspace
is not changed. Every other call goes through unchanged.
"""

from collections.abc import Callable

from agent.tools.base import ErrorType, ToolResult
from eval.schema import Fault

ToolFn = Callable[[str, dict], ToolResult]


def fault_result(tool: str, kind: str) -> ToolResult:
    if kind == "down":
        return ToolResult.failure(
            ErrorType.TOOL_UNAVAILABLE,
            f"The '{tool}' tool is unavailable right now. Try again, or use another tool.",
        )
    if kind == "timeout":
        return ToolResult.failure(
            ErrorType.TIMEOUT,
            f"The '{tool}' tool timed out. Try a smaller request.",
        )
    if kind == "server_error":
        return ToolResult.failure(
            ErrorType.TOOL_UNAVAILABLE,
            f"The '{tool}' service returned an internal server error (500). Try again.",
        )
    if kind == "empty":
        return ToolResult.success({})
    if kind == "bad_output":
        return ToolResult.success("<<garbled output ~~ ##>>")
    raise ValueError(f"Unknown fault kind {kind!r}.")


def inject_faults(functions: dict[str, ToolFn], faults: list[Fault]) -> dict[str, ToolFn]:
    """Return a copy of the tool functions with the scenario's faults applied."""
    plan: dict[str, dict[int, str]] = {}
    for fault in faults:
        if fault.tool not in functions:
            raise ValueError(f"Scenario fault refers to unknown tool {fault.tool!r}.")
        plan.setdefault(fault.tool, {})[fault.at_call] = fault.kind

    wrapped = dict(functions)
    for tool, calls in plan.items():
        wrapped[tool] = _wrap(tool, functions[tool], calls)
    return wrapped


def _wrap(tool: str, real: ToolFn, calls: dict[int, str]) -> ToolFn:
    count = 0

    def faulty(workspace: str, args: dict) -> ToolResult:
        nonlocal count
        count += 1
        kind = calls.get(count)
        if kind is None:
            return real(workspace, args)
        return fault_result(tool, kind)

    return faulty