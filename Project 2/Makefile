.PHONY: setup qdrant-up qdrant-down index run test eval-retrieval eval-generation ablation

setup:
	uv sync
	docker compose up -d qdrant

qdrant-up:
	docker compose up -d qdrant

qdrant-down:
	docker compose down

index:
	PYTHONPATH=src uv run python -c "from orchestrator.orchestrator import build_pipeline; build_pipeline().run()"

run:
	PYTHONPATH=src uv run uvicorn service.api:app --app-dir src --host 0.0.0.0 --port 8000

test:
	uv run pytest -q

eval-retrieval:
	PYTHONPATH=src uv run python -m evaluation.evaluate

# dense/sparse/hybrid/hybrid+reranker ablation is produced by the same run as eval-retrieval
ablation: eval-retrieval

eval-generation:
	PYTHONPATH=src uv run python -m evaluation.generation_eval
