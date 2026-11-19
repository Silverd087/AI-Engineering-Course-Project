# Postmortem — Project 0 Bake-Off

## What went wrong

1. **The scorer did not run on Windows.** `score.py` used `signal.SIGALRM` for the 5-second query timeout. That signal does not exist on Windows, so on our benchmark machine every run crashed before scoring one item. We replaced it with SQLite's progress handler: it checks a deadline every 10k VM steps and aborts the query. We tested it with an infinite recursive CTE, which now stops after 1 s and is labelled `timeout`.

2. **"Temperature 0 for all three" was not possible.** The brief asks for temperature 0. OpenAI's reasoning models (the gpt-5 family) reject any `temperature` other than the default, and they always reason before answering. So the API models run at their default sampling, and we gave both the same reasoning effort (`low`) to keep them comparable. The local model runs at temperature 0. This is one deviation we cannot remove, and it is stated in the report. The hidden reasoning tokens are billed as output, so they are in the API models' cost and latency. We also started on a different provider and switched to OpenAI when the course gave us an OpenAI key; keeping every provider-specific detail in `src/config.py` and one function in `run.py` made that a small change.

3. **Some of our first questions had no good answer.** Questions like "customers with no orders" and "books that were never sold" returned empty results, because in our seed data every customer and every book appears in an order. An empty expected result is a weak test, since many wrong queries also return nothing. "Which author has the most books?" had a four-way tie, so `LIMIT 1` would pick an arbitrary author. We now check every reference query for empty or NULL results and every `LIMIT` query for ties at the cut-off, and we rewrote the bad items (e.g. "authors with exactly 3 books").

4. **Hidden retries would have distorted latency.** By default the SDK silently retries 429/5xx errors. A retried call would report the combined time of several attempts as one latency. We turned SDK retries off, retry only on rate-limit and connection errors, and time only the attempt that succeeded. A rerun re-attempts only `api_error` rows (e.g. a missing key). Timeouts and refusals stay in as wrong answers, so we can't quietly rerun until a model passes.

5. **Repo hygiene.** An earlier upload put a `postmortem.md` and a `results/` folder for this project at the repository root instead of in `Project 0/`. Its `self_test.csv` referenced 73 items that no longer existed in `items.jsonl`. We rebuilt the items here and treat this folder as the only source of truth.

6. **The scorer ignores ORDER BY.** Result sets are compared as sorted multisets, so a query with the right rows in the wrong order still scores as correct. We chose this on purpose (strict ordering would fail correct queries that break ties differently), but it means we do not measure sort order.

## After the real run (fill in)

- Most common failure type per model, from `results/summary.csv`:
- Surprises in the wrong answers (e.g. extra columns, integer division in q050, NOT IN vs NULLs):
- Anything that broke during the run (rate limits, Ollama crashes, VRAM):

## What we learned

- Compare executed results, not SQL strings. Different SQL for the same answer is the normal case, not an edge case.
- An eval is only as good as its labels. Empty results and ties hide behind plausible-looking questions, and only running every reference query found them.
- "Same settings for every model" has to be checked against what each API actually accepts. Where it can't be made identical, write the difference down rather than hiding it.
- Build every table from one per-item CSV. The README table, the report and the web UI all read the same files, so they can't disagree.
