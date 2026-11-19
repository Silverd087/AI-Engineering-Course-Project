from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from agent.config import Limits, Settings
from agent.trace import read_trace
from eval import run_eval
from eval.schema import Fault, Scenario

SETTINGS = Settings(
    model="test",
    price_input_per_mtok=0.0,
    price_output_per_mtok=0.0,
    limits=Limits(max_steps=6, max_cost_usd=0.20, max_repeats=3, task_timeout_s=60.0),
)


class ScriptedModel:
    def __init__(self, replies):
        self.replies = list(replies)

    def invoke(self, messages):
        return self.replies.pop(0)


def scripted(replies):
    return lambda settings, schemas: ScriptedModel(replies)


def make_repo(root: Path) -> Path:
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path, monkeypatch):
    workspace_dir = make_repo(tmp_path / "workspace")
    monkeypatch.setattr(
        run_eval, "create_workspace",
        lambda fixture, run_id: SimpleNamespace(path=workspace_dir, remote=None),
    )
    return workspace_dir


def scenario(approver="approve_all", faults=None):
    return Scenario(
        id="s1",
        fixture="unused",
        migration="m",
        task="Change x to 2.",
        allowed_files=["src/**"],
        expected_steps=[],
        approver=approver,
        faults=faults or [],
    )


def edit_call():
    return AIMessage(content="", tool_calls=[
        {"name": "edit_file", "args": {"path": "src/a.py", "old": "x = 1", "new": "x = 2"}, "id": "e1"},
    ])


def finish_call(status="success"):
    return AIMessage(content="", tool_calls=[
        {"name": "finish", "args": {"summary": "ok", "status": status}, "id": "f1"},
    ])


def test_approved_edit_is_applied_and_scored(repo, tmp_path):
    row = run_eval.run_scenario(scenario(), SETTINGS, scripted([edit_call(), finish_call()]), tmp_path / "results")
    assert (repo / "src" / "a.py").read_text(encoding="utf-8") == "x = 2\n"
    assert row["stop_reason"] == "done"
    assert row["finish_status"] == "success"
    assert row["tests_pass"] is True
    assert row["approvals"] == ["y"]
    assert row["error"] is None


def test_quit_at_first_write_leaves_the_file_alone(repo, tmp_path):
    row = run_eval.run_scenario(
        scenario(approver="quit_at_first_write"), SETTINGS, scripted([edit_call(), finish_call()]), tmp_path / "results"
    )
    assert (repo / "src" / "a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert row["stop_reason"] == "user_quit"
    assert row["approvals"] == ["q"]


def test_gave_up_is_recorded_as_gave_up(repo, tmp_path):
    row = run_eval.run_scenario(scenario(), SETTINGS, scripted([finish_call("gave_up")]), tmp_path / "results")
    assert row["finish_status"] == "gave_up"


def test_fault_is_applied_during_the_run(repo, tmp_path):
    read = AIMessage(content="", tool_calls=[{"name": "read_file", "args": {"path": "src/a.py"}, "id": "r1"}])
    faults = [Fault(tool="read_file", at_call=1, kind="down")]
    row = run_eval.run_scenario(
        scenario(faults=faults), SETTINGS, scripted([read, finish_call()]), tmp_path / "results"
    )
    assert row["stop_reason"] == "done"
    records = read_trace(row["trace"])
    assert records[0].tool == "read_file"
    assert records[0].ok is False
    assert records[0].error_type == "tool_unavailable"


def test_summary_records_the_run_id_and_trace_path(repo, tmp_path):
    row = run_eval.run_scenario(scenario(), SETTINGS, scripted([finish_call()]), tmp_path / "results")
    assert len(row["run_id"]) == 32
    assert Path(row["trace"]).parent.name == "traces"