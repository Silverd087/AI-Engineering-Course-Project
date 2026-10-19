# Project 0 Postmortem

## What went wrong

The repository started with a working SQLite schema, seed database, and 10 starter questions, but several required benchmark components were still missing: the dataset was below the 50-test-item requirement, and the model runner, cost/latency aggregation, results artifacts, report, and hardware note had not been implemented.

During dataset expansion, two apparently valid LEFT JOIN questions produced empty result sets with the current seed data. They were removed rather than kept as weak benchmark cases, because the brief asks for questions where wrong SQL produces a visibly different, non-trivial result. The remaining 73 items were executed against the reference database and their reference queries all ran successfully with non-empty results.

## What we learned

The evaluator must compare executed result sets rather than SQL strings because multiple SQL formulations can be equivalent. The same prompt, temperature, token cap, parser, item order, and test set must be used for all three models. Parse errors, refusals, SQL errors, and timeouts must count as wrong instead of being manually repaired.

Real API/local measurements are intentionally not fabricated in this repository. They must be produced on the team's machine using the configured model names, API keys, and local Ollama model, then committed as `results/per_item.csv` and `results/summary.csv`.

## Next benchmark step

Run the commands in `README.md`, record the exact model names and hardware, inspect three wrong answers per model, and then export the final two-page report.
