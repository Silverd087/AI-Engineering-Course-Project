"""Builds and compiles the LangGraph StateGraph (task A4).

TODO: build_graph(checkpointer) -> compiled graph
  START -> agent -> route_after_agent -> {approve, tools, END}
  approve -> tools | agent | END
  tools   -> agent
  compile(checkpointer=...) and invoke with config={"recursion_limit": 2 * max_steps + 5}

Nodes live in nodes.py (agent, tools, router) and checkpoint.py (approve).
LLM setup and cost accounting live in llm.py.
"""
