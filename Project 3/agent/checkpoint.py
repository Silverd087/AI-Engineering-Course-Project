"""Human checkpoint: the `approve` node (task A5).

TODO:
- approve_node(state): for each write call, interrupt({"tool", "args", "diff"})
  and resume with "y" | "n" | "q"
- "n" -> ToolMessage carrying ToolResult.failure(ErrorType.REJECTED_BY_HUMAN, ...)
- "q" -> stop_reason = "user_quit"
- ScriptedApprover for eval: approve_all / reject_nth / reject_outside_allowed
"""
