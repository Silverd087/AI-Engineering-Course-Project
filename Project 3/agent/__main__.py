"""CLI entry point: `uv run python -m agent --scenario <id>` (task A8)."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="Run the migration agent on a scenario.")
    parser.add_argument("--scenario", required=True, help="scenario id from eval/scenarios/")
    args = parser.parse_args()
    raise SystemExit(f"Agent not implemented yet (scenario {args.scenario!r}).")


if __name__ == "__main__":
    main()
