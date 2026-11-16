from langchain_openai import ChatOpenAI

from agent.config import Settings


def build_model(settings: Settings, tools: list) -> object:
    model = ChatOpenAI(model=settings.model)
    return model.bind_tools(tools)


def cost_of(message, settings: Settings) -> float:
    usage = getattr(message, "usage_metadata", None) or {}
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    return (
        tokens_in / 1_000_000 * settings.price_input_per_mtok
        + tokens_out / 1_000_000 * settings.price_output_per_mtok
    )