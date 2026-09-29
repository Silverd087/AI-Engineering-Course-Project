# Project 0 — Bake-Off: Write SQL from a Question

CS496 AI Engineering · Fall 2026 · Dr Abdeldjalil Labed
Team: 3 members · Weight: 5% of final grade
Deadline: repo frozen before the first session of Week 2 · Demo: first session of Week 2

## The Task

Given a natural-language question, generate a SQL query that answers it. We compare three models — one top API model, one cheap API model, and one open-weights model we run ourselves — under identical conditions, on at least 50 test items.

Correctness is checked automatically: run the generated query and the reference query against the same database, and compare results (not string-matching the SQL itself). "Database" here means a small local SQLite file seeded with a few rows per schema — no production infrastructure needed, just enough data that a wrong query returns a visibly different result.

## Models Under Test

| Role | Model | Notes |
|---|---|---|
| Top API model | TBD (e.g. Claude Opus 5, top GPT/Gemini) | via API |
| Cheap API model | TBD (e.g. Claude Haiku 4.5, "mini"/"Flash") | via API |
| Open-weights model | TBD (Llama, Qwen, Gemma, Mistral, Phi, 1B–14B) | run locally via Ollama / llama.cpp / vLLM |

Same prompt, temperature 0, same output-token limit, same 50 items in the same order, same parser for all three. No per-model prompt tweaks, no dropping items a model fails, no hand-fixing outputs.

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd "Project 0"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API keys as environment variables (never commit them)
export TOP_MODEL_API_KEY=...
export CHEAP_MODEL_API_KEY=...
```

## Run

```bash
# Generate + score SQL for all three models
python src/run.py --items data/items.jsonl --out results/per_item.csv

# Build the summary table (accuracy, cost/1k, p50/p95 latency)
python src/cost.py --in results/per_item.csv --out results/summary.csv
```

## Repo Structure

```
Project 0/
├── README.md
├── data/
│   └── items.jsonl        # 50+ (question, db, reference query, expected result) items + labelling note
├── src/
│   ├── prompt.txt          # the single shared prompt
│   ├── run.py               # calls all 3 models, saves raw outputs
│   ├── score.py             # executes generated vs reference SQL, compares results
│   └── cost.py               # computes cost/1k requests, p50/p95 latency
├── results/
│   ├── per_item.csv        # one row per test item per model
│   ├── summary.csv          # aggregated accuracy / cost / latency
│   └── hardware_note.md     # specs used for the open-weights model
├── report.pdf                # 2-page report (see brief)
└── postmortem.md             # 1-page: what went wrong, what we learned
```

## Results

*(Fill in after runs — accuracy is n/50, not just %; a parse error, refusal, or timeout counts as wrong.)*

| Model | Accuracy (n/50) | Cost / 1k requests | Latency p50 (ms) | Latency p95 (ms) |
|---|---|---|---|---|
| Top API model | | | | |
| Cheap API model | | | | |
| Open-weights model | | | | |

**3 wrong answers per model:** to be added to `report.pdf`, with the query, expected result, and actual result.

**Our choice:** *(one paragraph — which model we'd use, and what would make us switch)*

## Task Division (3 people)

### Member A — Data & Evaluation Lead
- Build `data/items.jsonl`: 50+ (question, database schema, reference SQL, expected result) pairs, drawn from a public dataset (e.g. Spider) or hand-written against a chosen schema
- Create the small seeded SQLite file(s) the queries run against — just enough rows to make wrong queries return visibly wrong results (no production DB or server needed)
- Write the labelling note: where questions came from, how correctness was verified (two people check every label)
- Own `src/score.py`: executes both the generated and reference SQL against the local SQLite file(s), compares result sets (not raw text), returns right/wrong
- Own the dev/test split and the "one example item" write-up for the report

### Member B — Model Runner Lead
- Own `src/run.py`: calls all three models with the identical prompt, temperature 0, same output-token cap, same item order
- Set up and run the open-weights model locally (Ollama/llama.cpp/vLLM), including the hardware note (spec, tokens/sec)
- Manage API keys via environment variables (confirm none land in the repo)
- Write the "Setup" section of the report: model names, exact versions/dates, settings, hardware

### Member C — Cost, Latency & Reporting Lead
- Own `src/cost.py`: computes cost per 1k requests (API token usage × list price; hardware cost/hour ÷ throughput for the local model), and p50/p95 latency from real timed runs (50+ calls per model)
- Project cost at 100× traffic and compute the API-vs-self-hosted break-even volume
- Assemble `report.pdf` (2 pages) and `postmortem.md` (1 page — must include real problems, not just a clean success story)
- Compile `results/summary.csv` and the final results table above

### Shared (all three)
- Agree on the task/schema and get instructor sign-off by Day 2
- Review each other's 3 wrong-answer examples before they go in the report
- Contributions section below

## Contributions

| Member | Contribution |
|---|---|
| Member A | |
| Member B | |
| Member C | |

## Rules Checklist

- [ ] Runs from a clean clone
- [ ] Has an automatic eval (`score.py`)
- [ ] Has a cost model (`cost.py`)
- [ ] Has a postmortem with real problems
- [ ] Every line is explainable by the team
- [ ] No API keys in the repo
