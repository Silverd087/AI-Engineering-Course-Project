import pytest

from agent.trace import TraceRecord
from eval.metrics import (
    compute_metrics,
    forbidden_hit,
    percentile,
    run_succeeded,
    step_accuracy,
    tool_call_precision,
    wasted_steps,
)
from eval.schema import Fault, Injection, Scenario, Step, Success


def rec(tool, args=None, ok=True, approved=None, error_type=None):
    return TraceRecord(
        run_id="r", step=1, tool=tool, args=args or {}, ok=ok, approved=approved,
        error_type=error_type, t_start=0.0, t_end=0.1,
    )


def scenario(**overrides):
    base = dict(
        id="s1", fixture="f", migration="m", task="t", allowed_files=["src/**"],
        expected_steps=[Step(tool="read_file", args={"path": "a.py"}), Step(tool="edit_file", args={"path": "a.py"})],
        forbidden=[Step(tool="edit_file", args={"path_glob": "tests/**"})],
        success=Success(tests_pass=True, pr_opened=True, status="success", max_steps=5),
    )
    base.update(overrides)
    return Scenario(**base)


def row(**overrides):
    base = dict(
        scenario="s1", run_id="r", stop_reason="done", finish_status="success", tests_pass=True,
        pr_opened=True, steps=2, cost_usd=0.01, seconds=1.0, approvals=["y"], trace="t.jsonl", error=None,
    )
    base.update(overrides)
    return base


def test_step_accuracy_full_in_order():
    records = [rec("read_file", {"path": "a.py"}), rec("edit_file", {"path": "a.py"})]
    assert step_accuracy(scenario().expected_steps, records) == 1.0


def test_step_accuracy_counts_only_steps_found_in_order():
    records = [rec("edit_file", {"path": "a.py"}), rec("read_file", {"path": "a.py"})]
    assert step_accuracy(scenario().expected_steps, records) == 0.5


def test_precision_is_share_of_calls_that_match_expected():
    records = [rec("read_file", {"path": "a.py"}), rec("list_files", {"glob": "*"})]
    assert tool_call_precision(scenario().expected_steps, records) == 0.5


def test_wasted_steps_counts_failures_and_exact_repeats():
    records = [
        rec("read_file", {"path": "a.py"}),
        rec("read_file", {"path": "a.py"}),
        rec("edit_file", {"path": "a.py"}, ok=False),
    ]
    assert wasted_steps(records) == 2


def test_forbidden_path_glob_is_a_hit():
    assert forbidden_hit(scenario().forbidden, [rec("edit_file", {"path": "tests/test_a.py"})])


def test_rejected_forbidden_write_is_not_a_hit():
    records = [rec("edit_file", {"path": "tests/test_a.py"}, approved=False)]
    from eval.metrics import executed
    assert not forbidden_hit(scenario().forbidden, executed(records))


def test_success_requires_every_criterion():
    records = [rec("read_file", {"path": "a.py"}), rec("edit_file", {"path": "a.py"})]
    assert run_succeeded(row(), scenario(), records)
    assert not run_succeeded(row(tests_pass=False), scenario(), records)
    assert not run_succeeded(row(finish_status="gave_up"), scenario(), records)
    assert not run_succeeded(row(steps=9), scenario(), records)


def test_forbidden_step_fails_an_otherwise_good_run():
    records = [rec("edit_file", {"path": "tests/test_a.py"})]
    assert not run_succeeded(row(), scenario(), records)


def test_percentile_uses_nearest_rank():
    values = list(range(1, 11))
    assert percentile(values, 50) == 5
    assert percentile(values, 95) == 10


def test_aggregate_rates_and_cost_at_100x(tmp_path):
    traces = {}
    good = tmp_path / "good.jsonl"
    bad = tmp_path / "bad.jsonl"
    traces[str(good)] = [rec("read_file", {"path": "a.py"}), rec("edit_file", {"path": "a.py"})]
    traces[str(bad)] = [rec("edit_file", {"path": "tests/x.py"})]
    rows = [
        row(trace=str(good), cost_usd=0.02),
        row(trace=str(bad), finish_status="gave_up", tests_pass=False, cost_usd=0.04, steps=1),
    ]
    report = compute_metrics(rows, {"s1": scenario()}, load=lambda p: traces[str(p)])
    agg = report["aggregate"]
    assert agg["tasks"] == 2
    assert agg["task_success_rate"] == 0.5
    assert agg["mean_cost_usd_per_task"] == pytest.approx(0.03)
    assert agg["cost_at_100x_usd"] == pytest.approx(3.0)


def test_recovery_and_injection_are_none_when_not_applicable(tmp_path):
    trace = tmp_path / "t.jsonl"
    report = compute_metrics([row(trace=str(trace))], {"s1": scenario()}, load=lambda p: [])
    assert report["aggregate"]["recovery_after_failure_rate"] is None
    assert report["aggregate"]["injection_cases_resisted"] is None


def test_recovery_rate_counts_only_faulted_scenarios(tmp_path):
    faulted = scenario(id="f1", faults=[Fault(tool="read_file", at_call=1, kind="down")])
    trace = tmp_path / "t.jsonl"
    report = compute_metrics(
        [row(scenario="f1", trace=str(trace))], {"f1": faulted}, load=lambda p: [],
    )
    assert report["aggregate"]["recovery_after_failure_rate"] == 1.0


def test_injection_resisted_when_no_forbidden_step(tmp_path):
    inj = scenario(id="i1", injection=Injection(surface="code_comment", file="src/a.py", payload="x"))
    trace = tmp_path / "t.jsonl"
    report = compute_metrics([row(scenario="i1", trace=str(trace))], {"i1": inj}, load=lambda p: [])
    assert report["aggregate"]["injection_cases_resisted"] == "1/1"


def test_recursion_error_is_a_stop_rule_violation(tmp_path):
    trace = tmp_path / "t.jsonl"
    report = compute_metrics(
        [row(trace=str(trace), stop_reason=None, error="GraphRecursionError: limit")],
        {"s1": scenario()}, load=lambda p: [],
    )
    assert report["aggregate"]["stop_rule_violations"] == 1