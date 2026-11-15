"""Scenario format (README section 5, interface 3). Every YAML in eval/scenarios/ must validate."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Step(BaseModel):
    """One expected or forbidden step: a tool name plus the args that must match (subset match)."""

    model_config = ConfigDict(extra="forbid")

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


def _to_step(raw: Any) -> Any:
    # YAML shorthand: "run_tests"  or  {"edit_file": {"path": "src/x.py"}}
    if isinstance(raw, str):
        return {"tool": raw}
    if isinstance(raw, dict) and len(raw) == 1 and "tool" not in raw:
        (tool, args), = raw.items()
        return {"tool": tool, "args": args or {}}
    return raw


class Fault(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    at_call: int = 1                    # 1 = the first call to this tool fails
    kind: Literal["down", "timeout", "empty", "bad_output", "server_error"]


class Injection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: Literal["code_comment", "docstring", "test_output", "readme", "pr_template", "error_message"]
    file: str | None = None             # where the payload is planted (if file-based)
    payload: str


class Success(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tests_pass: bool = True
    pr_opened: bool = True
    status: Literal["success", "gave_up"] = "success"
    max_steps: int | None = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    fixture: str                        # folder name in sandbox/fixtures/
    migration: str                      # e.g. utcnow, pathlib, unittest_to_pytest, legacy_sdk
    task: str
    allowed_files: list[str] = Field(default_factory=lambda: ["src/**"])  # globs the agent may edit
    expected_steps: list[Step]
    forbidden: list[Step] = Field(default_factory=list)
    faults: list[Fault] = Field(default_factory=list)
    injection: Injection | None = None
    approver: Literal["approve_all", "reject_first_write", "reject_outside_allowed", "quit_at_first_write"] = "approve_all"
    success: Success = Field(default_factory=Success)

    @field_validator("expected_steps", "forbidden", mode="before")
    @classmethod
    def _shorthand(cls, v: Any) -> Any:
        return [_to_step(x) for x in v] if isinstance(v, list) else v


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def load_scenarios(directory: str | Path) -> list[Scenario]:
    return [load_scenario(p) for p in sorted(Path(directory).glob("*.yaml"))]
