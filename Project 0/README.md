# Project 0 — Bake-Off: Write SQL from a Question

CS496 AI Engineering · Fall 2026 · Dr Abdeldjalil Labed
Team: 3 members · Weight: 5% of final grade
Deadline: repo frozen before the first session of Week 2 · Demo: first session of Week 2

## The Task

Given a natural-language question and the schema of a small bookstore database, a model writes one SQLite query. We compare three models (a top API model, a cheap API model and an open-weights model we run ourselves) under identical conditions on **50 frozen test items** (+10 dev items).

Correctness is checked automatically. We run the generated query and the reference query against the same local SQLite file and compare the **result sets**, not the SQL text. Equivalent queries written differently therefore both score as correct. A parse error, SQL error, refusal or timeout counts as wrong.

## Models Under Test

| Role | Model | How it runs |
|---|---|---|
| Top API model | `gpt-5` | OpenAI API |
| Cheap API model | `gpt-5-mini` | OpenAI API |
| Open-weights model | `qwen2.5-coder:7b` (Q4_K_M) | Ollama on our own laptop (RTX 4060 8 GB), see `results/hardware_note.md` |

All three get the same prompt (`src/prompt.txt`), the same items in the same order, the same output cap (2048 tokens), the same timeout and the same parser (`extract_sql` in `src/run.py`). The local model runs at temperature 0. **Deviation:** OpenAI reasoning models (gpt-5 family) reject a `temperature` setting, so both API models run at their default sampling with reasoning effort `low`. Their reasoning tokens are billed as output and are included in the cost. Model names can be overridden with `TOP_MODEL`, `CHEAP_MODEL` and `LOCAL_MODEL`. If you change a model, add its list price to `PRICES_PER_MTOK` in `src/config.py`, and check the prices there against https://openai.com/api/pricing on the day you run.

## Setup (one command)

```bash
pip install -r requirements.txt
```

You also need:
- the OpenAI API key, never in the repo: put `OPENAI_API_KEY=sk-...` in `Project 0/.env` (git-ignored, loaded automatically) or export it in your shell.
- [Ollama](https://ollama.com) running locally, with the model pulled: `ollama pull qwen2.5-coder:7b`

## Run (one command)

```bash
python src/bench.py
```

This builds `data/bookstore.db`, self-tests the scorer (60/60 expected), calls all three models one request at a time, scores them, builds the cost/latency summary and writes `report.pdf`. An interrupted run resumes where it stopped. Individual steps:

```bash
python data/build_db.py                       # build the SQLite DB from schema.sql + seed.sql
python src/score.py --items data/items.jsonl --db data/bookstore.db --self-test --out results/self_test.csv
python src/run.py [--models top,cheap,local] [--split test] [--limit 5]   # -> results/raw_outputs.jsonl
python src/score.py --items data/items.jsonl --db data/bookstore.db --candidates results/raw_outputs.jsonl --out results/per_item.csv
python src/cost.py                            # -> results/summary.csv, results/cost_model.json
python src/report.py                          # -> report.pdf (1 page) + refreshes the table below
```

## Web frontend

```bash
python app/server.py        # open http://127.0.0.1:5000
```

- **Results**: per-model accuracy (n/50), p50/p95 latency, cost per 1k, failure breakdown, monthly cost at 100× and break-even, and a grid of every item × model. Click any cell to see the question, the reference SQL, each model's SQL and what it returned.
- **Playground**: send a test item or your own question to any of the three models side by side. It uses the same prompt, parser and scorer as the benchmark and shows the SQL, the rows returned and right/wrong. Playground calls are not saved to `results/`.
- **Data**: schema, prompt, settings and all 60 labelled items.

## Results

<!-- RESULTS:START -->
*Not run yet. `python src/bench.py` fills this table from `results/summary.csv`.*
<!-- RESULTS:END -->

**3 wrong answers per model** and **our choice** are in `report.pdf` (the choice text lives in `results/choice.md`).

## Repo Structure

```
Project 0/
├── README.md
├── requirements.txt
├── data/
│   ├── schema.sql, seed.sql  # bookstore DB: authors, books, customers, orders, order_items
│   ├── build_db.py           # builds data/bookstore.db
│   ├── items.jsonl           # 60 items: {id, question, reference_sql, category, split}
│   └── labelling_note.md     # where items came from, how labels were checked, dev/test split
├── src/
│   ├── config.py             # models, shared settings, prices, self-hosting cost assumptions
│   ├── prompt.txt            # the single shared prompt
│   ├── run.py                # calls the models (OpenAI Responses API + Ollama), times them, parses SQL -> results/raw_outputs.jsonl
│   ├── score.py              # executes candidate vs reference SQL, compares result sets
│   ├── cost.py               # accuracy, p50/p95, cost/1k, 100x, break-even -> summary.csv
│   ├── report.py             # report.pdf (1 page) from the results files
│   └── bench.py              # runs everything in order
├── app/                      # Flask frontend (server.py + static/index.html)
├── results/
│   ├── raw_outputs.jsonl     # every raw model answer, with usage + latency
│   ├── per_item.csv          # one scored row per item per model
│   ├── summary.csv, cost_model.json
│   ├── choice.md             # our written decision (goes into the report)
│   └── hardware_note.md
├── report.pdf
└── postmortem.md
```

## Task Division (3 people)

### Member A — Data & Evaluation Lead
- `data/items.jsonl` (60 items, dev/test split), seed DB, `data/labelling_note.md`
- `src/score.py`: result-set comparison, failure classes, Windows-safe timeout
- The dev/test split and the example item in the report

### Member B — Model Runner Lead
- `src/run.py` + `src/prompt.txt`: identical prompt, settings, item order and parser for all three models
- Local model setup with Ollama, `results/hardware_note.md` (spec, tokens/s)
- API keys via environment variables only; the Setup section of the report

### Member C — Cost, Latency & Reporting Lead
- `src/cost.py`: cost per 1k requests, p50/p95, 100× projection, break-even volume
- `src/report.py`, `report.pdf`, `postmortem.md`, `results/choice.md`, the web frontend (`app/`)

### Shared
- Instructor sign-off on the task by Day 2
- Review each other's 3 wrong-answer examples before they go in the report

## Contributions

| Member | Contribution |
|---|---|
| Member A | |
| Member B | |
| Member C | |

## Rules Checklist

- [x] Runs from a clean clone (`pip install -r requirements.txt` then `python src/bench.py`)
- [x] Has an automatic eval (`src/score.py`, no human or LLM in the loop)
- [x] Has a cost model (`src/cost.py`, assumptions in `src/config.py`)
- [ ] Has a postmortem with real problems (`postmortem.md`, finish after the real run)
- [ ] Every line is explainable by the team
- [x] No API keys in the repo
