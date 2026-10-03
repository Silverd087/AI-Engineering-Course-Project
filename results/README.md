# Results

This directory is intentionally committed with the required artifact locations. Benchmark CSVs must be generated from real runs and must not contain invented measurements.

Expected files:
- `per_item.csv` — one scored row per test item per model.
- `summary.csv` — aggregated accuracy, parse/error count, p50/p95 latency, token usage and cost/1k.
- `hardware_note.md` — actual local machine/model information.
