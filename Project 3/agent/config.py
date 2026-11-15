"""Runtime settings, read from environment variables (and .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Limits:
    """The stop rule's limits (README section 2, 'Stopping condition')."""

    max_steps: int = 25
    max_cost_usd: float = 0.20
    max_repeats: int = 3          # same tool + same args this many times in a row -> stop
    task_timeout_s: float = 300.0


@dataclass(frozen=True)
class Settings:
    model: str
    price_input_per_mtok: float   # USD per 1M input tokens, for the cost meter
    price_output_per_mtok: float
    limits: Limits = field(default_factory=Limits)


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        model=os.getenv("AGENT_MODEL", ""),
        price_input_per_mtok=float(os.getenv("PRICE_INPUT_PER_MTOK", "0")),
        price_output_per_mtok=float(os.getenv("PRICE_OUTPUT_PER_MTOK", "0")),
        limits=Limits(
            max_steps=int(os.getenv("MAX_STEPS", "25")),
            max_cost_usd=float(os.getenv("MAX_COST_USD", "0.20")),
            max_repeats=int(os.getenv("MAX_REPEATS", "3")),
            task_timeout_s=float(os.getenv("TASK_TIMEOUT_S", "300")),
        ),
    )
