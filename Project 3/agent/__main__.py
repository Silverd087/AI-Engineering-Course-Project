"""CLI entry point: `uv run python -m agent --scenario <id>` (task A8)."""

import argparse
import time
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agent.config import load_settings
from agent.graph import build_graph
from agent.llm import build_model
from agent.tools import build_tools
from agent.trace import TraceWriter
from eval.schema import load_scenarios
from sandbox.manager import create_workspace
from sandbox.mock_pr_server import MockPrServer

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "eval" / "scenarios"
RESULTS = ROOT / "eval" / "results"


def find_scenario(scenario_id: str):
    for scenario in load_scenarios(SCENARIOS):
        if scenario.id == scenario_id:
            return scenario
    raise SystemExit(f"No scenario named {scenario_id!r} in {SCENARIOS}.")


def ask_human(payload: dict) -> str:
    print(f"\n[CHECKPOINT] {payload['tool']}")
    print(payload["diff"])
    while True:
        answer = input("Approve? [y]es / [n]o / [q]uit > ").strip().lower()
        if answer in ("y", "n", "q"):
            return answer
        print("Please type y, n or q.")


def task_message(scenario) -> str:
    allowed = ", ".join(scenario.allowed_files)
    return f"{scenario.task}\n\nYou may only edit files matching: {allowed}."


def run(scenario_id: str) -> None:
    settings = load_settings()
    if not settings.model:
        raise SystemExit("AGENT_MODEL is not set. Copy .env.example to .env and fill it in.")

    scenario = find_scenario(scenario_id)
    run_id = uuid.uuid4().hex
    workspace = create_workspace(scenario.fixture, run_id)

    schemas, functions = build_tools(scenario.allowed_files, MockPrServer())
    model = build_model(settings, schemas)
    trace = TraceWriter(RESULTS / "traces" / f"{scenario.id}-{run_id}.jsonl")

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

    RESULTS.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(RESULTS / "checkpoints.sqlite")) as checkpointer:
        graph = build_graph(model, functions, settings, trace, run_id, checkpointer=checkpointer)
        result = graph.invoke(state, config)
        while "__interrupt__" in result:
            answer = ask_human(result["__interrupt__"][0].value)
            result = graph.invoke(Command(resume=answer), config)

    print(f"\nRun {run_id} finished: stop_reason={result['stop_reason']}, finish_status={result['finish_status']}")
    print(f"Trace: {trace.path}")
    print(f"Workspace: {workspace.path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="Run the migration agent on a scenario.")
    parser.add_argument("--scenario", required=True, help="scenario id from eval/scenarios/")
    args = parser.parse_args()
    run(args.scenario)


if __name__ == "__main__":
    main()
