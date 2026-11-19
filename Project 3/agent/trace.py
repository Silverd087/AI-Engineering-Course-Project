"""Trace format: one JSONL line per tool call (README section 7, interface 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class TraceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    step: int
    kind: Literal["tool", "model"] = "tool"  # "model" = the final model call, which ran no tool
    tool: str
    args: dict[str, Any]
    ok: bool
    error_type: str | None = None
    output_preview: str = ""        # first ~500 chars of the tool output
    approved: bool | None = None    # None for read tools; True/False for write tools
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    t_start: float
    t_end: float


class TraceWriter:
    """Appends TraceRecords to a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: TraceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")


def read_trace(path: str | Path) -> list[TraceRecord]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [TraceRecord.model_validate_json(line) for line in lines if line.strip()]