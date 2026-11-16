from types import SimpleNamespace

import pytest

from agent.config import Settings
from agent.llm import cost_of


@pytest.fixture
def settings():
    return Settings(model="test-model", price_input_per_mtok=2.0, price_output_per_mtok=8.0)


def test_cost_of_uses_input_and_output_prices(settings):
    message = SimpleNamespace(usage_metadata={"input_tokens": 1_000_000, "output_tokens": 500_000})
    assert cost_of(message, settings) == pytest.approx(2.0 + 4.0)


def test_cost_of_is_zero_without_usage(settings):
    message = SimpleNamespace()
    assert cost_of(message, settings) == 0.0