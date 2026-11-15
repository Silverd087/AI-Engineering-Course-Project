"""Tests for the shared interfaces (tool result, trace, scenario format)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.trace import TraceRecord, TraceWriter, read_trace
from agent.tools.base import ErrorType, StrictArgs, ToolResult
from eval.schema import load_scenarios

ROOT = Path(__file__).resolve().parents[1]


def test_tool_result_success_and_failure():
    assert ToolResult.success({"files": []}).ok
    fail = ToolResult.failure(ErrorType.NOT_FOUND, "File 'x.py' not found. Use list_files.")
    assert not fail.ok and fail.error_type == "not_found"
    assert '"error_type": "not_found"' in fail.to_json()


def test_tool_result_rejects_inconsistent_states():
    with pytest.raises(ValidationError):
        ToolResult(ok=False)  # failure without error_type/message
    with pytest.raises(ValidationError):
        ToolResult(ok=True, error_type=ErrorType.TIMEOUT)


def test_strict_args_reject_unknown_fields():
    class ReadFileArgs(StrictArgs):
        path: str

    with pytest.raises(ValidationError):
        ReadFileArgs(path="a.py", sneaky="rm -rf /")


def test_trace_roundtrip(tmp_path):
    writer = TraceWriter(tmp_path / "run.jsonl")
    rec = TraceRecord(run_id="r1", step=1, tool="read_file", args={"path": "a.py"}, ok=True, t_start=0.0, t_end=0.1)
    writer.write(rec)
    writer.write(rec.model_copy(update={"step": 2}))
    assert [r.step for r in read_trace(tmp_path / "run.jsonl")] == [1, 2]


def test_all_scenarios_validate():
    scenarios = load_scenarios(ROOT / "eval" / "scenarios")
    assert scenarios, "no scenarios found"
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids)), "duplicate scenario ids"
    first = scenarios[0]
    assert first.expected_steps[0].tool == "run_tests"
