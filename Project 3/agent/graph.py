"""Builds and compiles the LangGraph StateGraph (task A4, A5)."""

import time

from langgraph.graph import END, START, StateGraph

from agent.checkpoint import approve_node
from agent.nodes import agent_node, route_after_agent, route_after_approve, stop_node, tools_node
from agent.state import AgentState


def build_graph(model, tools, settings, trace, run_id, checkpointer=None):
    limits = settings.limits

    def agent(state: AgentState) -> dict:
        return agent_node(state, model, settings)

    def run_tools(state: AgentState) -> dict:
        return tools_node(state, tools, trace, run_id)

    def approve(state: AgentState) -> dict:
        return approve_node(state, trace, run_id)

    def stop(state: AgentState) -> dict:
        return stop_node(state, limits, now=time.monotonic())

    def route(state: AgentState) -> str:
        return route_after_agent(state, limits, now=time.monotonic())

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent)
    builder.add_node("tools", run_tools)
    builder.add_node("stop", stop)
    builder.add_node("approve", approve)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route, {"tools": "tools", "stop": "stop", "approve": "approve"})
    builder.add_conditional_edges("approve", route_after_approve, {"tools": "tools", "agent": "agent", "end": END})
    builder.add_edge("tools", "agent")
    builder.add_edge("stop", END)

    return builder.compile(checkpointer=checkpointer)