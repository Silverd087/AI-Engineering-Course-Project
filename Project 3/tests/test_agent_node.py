from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.config import Settings
from agent.nodes import agent_node
from agent.state import AgentState

SETTINGS = Settings(model="test-model", price_input_per_mtok=2.0, price_output_per_mtok=8.0)


class FakeModel:
    def __init__(self, reply):
        self.reply = reply
        self.seen = None

    def invoke(self, messages):
        self.seen = messages
        return self.reply


def make_state(**overrides) -> AgentState:
    base = AgentState(
        messages=[HumanMessage(content="migrate the repo")],
        workspace="/tmp/ws",
        steps=0,
        cost_usd=0.0,
        recent_calls=[],
        started_at=0.0,
        stop_reason=None,
    )
    base.update(overrides)
    return base


def test_agent_node_adds_model_reply_to_messages():
    reply = AIMessage(content="ok")
    model = FakeModel(reply)
    result = agent_node(make_state(), model, SETTINGS)
    assert result["messages"] == [reply]


def test_agent_node_sends_current_messages_to_model():
    model = FakeModel(AIMessage(content="ok"))
    state = make_state()
    agent_node(state, model, SETTINGS)
    assert model.seen == state["messages"]


def test_agent_node_adds_cost_to_running_total():
    reply = AIMessage(
        content="ok",
        usage_metadata={"input_tokens": 1_000_000, "output_tokens": 500_000, "total_tokens": 1_500_000},
    )
    result = agent_node(make_state(cost_usd=0.5), FakeModel(reply), SETTINGS)
    assert result["cost_usd"] == pytest.approx(0.5 + 2.0 + 4.0)