.PHONY: setup run test eval eval-injection sandbox-reset

SCENARIO ?= utcnow_basic

setup:
	uv sync

run:
	uv run python -m agent --scenario $(SCENARIO)

test:
	uv run pytest

eval:
	uv run python -m eval.run_eval

eval-injection:
	uv run python -m eval.run_eval --only injection

sandbox-reset:
	uv run python -m sandbox.manager reset
