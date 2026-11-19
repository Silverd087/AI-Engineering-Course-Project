"""Eval runner (task C3): `uv run python -m eval.run_eval [--only injection]`."""

import argparse
import json
import time
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.config import Settings, load_settings
from agent.graph import build_graph
from agent.llm import build_model
from agent.tools import build_tools
from agent.tools.run_tests import run_tests
from agent.trace import TraceWriter
from eval.approvers import make_approver
from eval.faults import inject_faults
from eval.injections import plant_injection
from eval.schema import Scenario, load_scenarios
from sandbox.manager import create_workspace
from sandbox.mock_pr_server import MockPrServer

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "eval" / "scenarios"
RESULTS = ROOT / "eval" / "results"


def task_message(scenario: Scenario) -> str:
    allowed = ", ".join(scenario.allowed_files)
    return f"{scenario.task}\n\nYou may only edit files matching: {allowed}."


def run_scenario(scenario: Scenario, settings: Settings, model_factory, results_dir: Path) -> dict:
    run_id = uuid.uuid4().hex
    workspace = create_workspace(scenario.fixture, run_id)
    planted = None
    if scenario.injection is not None:
        planted = plant_injection(workspace.path, scenario.injection)

    pr_api = MockPrServer(results_dir / "prs" / f"{run_id}.json")
    schemas, functions = build_tools(scenario.allowed_files, pr_api)
    functions = inject_faults(functions, scenario.faults)
    model = model_factory(settings, schemas)
    approver = make_approver(scenario.approver, scenario.allowed_files)
    trace = TraceWriter(results_dir / "traces" / f"{scenario.id}-{run_id}.jsonl")

    state = {
        "messages": [HumanMessage(content=task_message(scenario))],
        "workspace": str(workspace.path),
        "steps": 0,
        "cost_usd": 0.0,
        "recent_calls": [],
        "started_at": time.monotonic(),
        "stop_reason": None,
        "finish_status": None,
    }
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 2 * settings.limits.max_steps + 5,
    }
    graph = build_graph(model, functions, settings, trace, run_id, checkpointer=MemorySaver())

    started = time.monotonic()
    error = None
    result = {}
    try:
        result = graph.invoke(state, config)
        while "__interrupt__" in result:
            answer = approver(result["__interrupt__"][0].value)
            result = graph.invoke(Command(resume=answer), config)
    except Exception as exc:  # one broken scenario must not stop the whole eval
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.monotonic() - started

    tests = run_tests(str(workspace.path), {})
    return {
        "scenario": scenario.id,
        "run_id": run_id,
        "planted_in": planted,
        "stop_reason": result.get("stop_reason"),
        "finish_status": result.get("finish_status"),
        "tests_pass": bool(tests.ok and tests.result["passed"]),
        "pr_opened": bool(pr_api.list_prs()),
        "steps": result.get("steps", 0),
        "cost_usd": result.get("cost_usd", 0.0),
        "seconds": round(elapsed, 2),
        "approvals": approver.decisions,
        "trace": str(trace.path),
        "error": error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="eval.run_eval", description="Run the eval scenarios.")
    parser.add_argument("--only", choices=["injection"], default=None)
    args = parser.parse_args()

    settings = load_settings()
    if not settings.model:
        raise SystemExit("AGENT_MODEL is not set. Fill it in your .env file first.")

    scenarios = load_scenarios(SCENARIOS)
    if args.only == "injection":
        scenarios = [s for s in scenarios if s.injection is not None]

    RESULTS.mkdir(parents=True, exist_ok=True)
    summaries = []
    for scenario in scenarios:
        print(f"Running {scenario.id} ...")
        summaries.append(run_scenario(scenario, settings, build_model, RESULTS))

    (RESULTS / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    for row in summaries:
        print(f"{row['scenario']}: stop={row['stop_reason']} status={row['finish_status']} tests_pass={row['tests_pass']} error={row['error']}")
    print(f"\nSummary saved to {RESULTS / 'summary.json'}")


if __name__ == "__main__":
    main()