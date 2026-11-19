"""finish: the model's way to end a run. The router handles it, so it is never executed."""

from typing import Literal

from agent.tools.base import StrictArgs


class FinishArgs(StrictArgs):
    summary: str
    status: Literal["success", "gave_up"]