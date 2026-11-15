"""Graph nodes (task A4).

TODO:
- agent_node(state): call the model, add its cost to state["cost_usd"]
- tools_node(state): run validated tool calls, wrap outputs in UNTRUSTED tags,
  write one TraceRecord per call, increment state["steps"]
- route_after_agent(state): check check_stop() first, then return
  "approve" (write call) | "tools" (read/exec call) | END
"""
