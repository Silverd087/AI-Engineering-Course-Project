"""Shared tool contract. Every tool in agent/tools/ follows this.

Rules (see README sections 2 and 7):
- Inputs are a Pydantic model that subclasses ``StrictArgs`` (unknown fields are rejected).
- Tools never raise to the model. They return a ``ToolResult``: either
  ``ToolResult.success(result)`` or ``ToolResult.failure(ErrorType.X, "plain-English hint")``.
- The message in a failure must tell the model what to do next, e.g.
  "File 'src/x.py' not found. Use list_files to see available paths."
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class StrictArgs(BaseModel):
    """Base class for every tool's input schema: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class ErrorType(StrEnum):
    """Error classes a tool can report. Keep in sync with errors.md."""

    BAD_ARGUMENTS = "bad_arguments"          # schema-valid but meaningless (e.g. start_line > end_line)
    NOT_FOUND = "not_found"                  # file / test target does not exist
    OUTSIDE_WORKSPACE = "outside_workspace"  # path escapes the sandbox (../, absolute path)
    NOT_ALLOWED = "not_allowed"              # write to a file the migration spec does not allow
    NO_MATCH = "no_match"                    # edit_file: `old` text not found
    AMBIGUOUS_MATCH = "ambiguous_match"      # edit_file: `old` text found more than once
    TIMEOUT = "timeout"                      # run_tests or another call took too long
    TOOL_UNAVAILABLE = "tool_unavailable"    # tool down (real, or injected by eval/faults.py)
    REJECTED_BY_HUMAN = "rejected_by_human"  # human said "n" at the checkpoint
    INTERNAL = "internal_error"              # unexpected bug inside the tool (logged, hint returned)


class ToolResult(BaseModel):
    """What every tool returns. Serialised to JSON for the model."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    result: Any = None
    error_type: ErrorType | None = None
    message: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> "ToolResult":
        if self.ok and self.error_type is not None:
            raise ValueError("a successful ToolResult cannot have an error_type")
        if not self.ok and (self.error_type is None or not self.message):
            raise ValueError("a failed ToolResult needs an error_type and a message")
        return self

    @classmethod
    def success(cls, result: Any = None, message: str = "") -> "ToolResult":
        return cls(ok=True, result=result, message=message)

    @classmethod
    def failure(cls, error_type: ErrorType, message: str) -> "ToolResult":
        return cls(ok=False, error_type=error_type, message=message)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json", exclude_none=True), ensure_ascii=False)
