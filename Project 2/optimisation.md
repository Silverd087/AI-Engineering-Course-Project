# Optimisation (Week 8)

## The changes

The Week 7 pipeline calls an LLM to rewrite **every** question before retrieval, then runs a CPU cross-encoder reranker on every retrieval. Two measurements motivated cutting both:

1. **The retrieval ablation** (`design.md`) showed the reranker adds essentially no retrieval-quality improvement over hybrid search alone (hit@5 0.979 either way) for ~3.6 extra seconds of CPU inference per query — exactly the case the brief calls out: "skipping the reranker when the first search is confident."
2. **Checking the query rewriter against the eval set** showed 107 of 108 questions (99%) are already clear and single-topic — the rewriter was making a full LLM round-trip to return the question unchanged almost every time.

**Week 8 changes:**
- `use_reranker=False` by default (`src/generation/pipeline.py`).
- The rewriter now only fires when a cheap heuristic (`retrieval/query_rewriter.py::needs_rewrite`) flags the question as actually needing it: multiple course codes mentioned (likely multi-part), fewer than 4 words (too terse to trust as self-contained), an unresolved pronoun (`it`, `its`, `that`, ...), or an "and"-joined question with no course code to anchor on. Everything else skips straight to retrieval. This errs toward calling the rewriter when unsure — a spurious call is cheap, a skipped one that was actually needed costs retrieval quality.

## Before / after, measured on the same 108-question eval set

All numbers from `evaluation/generation_eval.py`, identical `data/eval/questions.json`, identical Qdrant index, identical `gpt-4o-mini` generation/judge model — only the two pipeline flags above changed. Baseline latency/cost is pooled or averaged across two independent runs to reduce noise from OpenAI API latency variance.

### Latency (end-to-end `/ask` request)

| Metric | Baseline (Week 7) | Optimised (Week 8) | Change |
|---|---|---|---|
| Retrieval step p50 | 5243ms | 124ms | **−97.6%** |
| Retrieval step p95 | 7153ms | 245ms | **−96.6%** |
| **Total request p50** | **7144ms** | **2829ms** | **−60.4%** |
| **Total request p95** | **9791ms** | **3687ms** | **−62.3%** |

Target met on both p50 and p95, comfortably clearing the 50% bar — and this is the *conservative* read, since the baseline here is pooled across two runs while the optimised number is a single run; the direction and magnitude are consistent with every earlier individual run in this session.

### Accuracy (same eval set, both configurations)

| Metric | Baseline | Optimised | Change |
|---|---|---|---|
| Faithfulness | 0.998 | 1.000 | +0.002 |
| Citation accuracy | 1.000 | 1.000 | 0 |
| Correctness | 0.977 | 0.989 | +0.012 |
| Correct "I don't know" rate | 1.000 | 1.000 | 0 |
| False "I don't know" rate | 0.064 | 0.043 | −0.021 (better) |

**Zero accuracy lost — every metric held steady or improved.** This tracks with the ablation: the reranker wasn't adding retrieval quality on this corpus, and the skipped rewrite calls were, by construction, only skipped for questions that didn't need rewriting.

### Cost per request

| Metric | Baseline | Optimised | Change |
|---|---|---|---|
| Input tokens / request (mean) | 1888 | 1870 | −1.0% |
| Output tokens / request (mean) | 24.7 | 26.1 | +5.7% |
| Generation cost / request (`gpt-4o-mini`: \$0.15/1M in, \$0.60/1M out) | \$0.000298 | \$0.000296 | −0.7% |

Cost per request is essentially flat. This is expected and worth stating plainly: the reranker and rewriter are not API-metered — the reranker is a local CPU model and the rewriter, when it runs, is one small call — so removing them doesn't touch the generation step's token usage (still the same `k=5` chunks reaching the LLM either way). **The win here is entirely latency, not generation cost.**

## Cost model: today and at 100x

Assumes a modest early-access baseline of **50 requests/day** (today) and **100x = 5,000 requests/day**. Embedding (dense + sparse) and reranking run locally (no API cost); the only metered cost is the generation call, plus the rewriter call on the ~1% of questions that trigger it (optimised pipeline).

| | Today (50 req/day) | At 100x (5,000 req/day) |
|---|---|---|
| Generation cost (`gpt-4o-mini`, \$0.000296/req) | \$0.015/day (~\$0.44/month) | \$1.48/day (~\$44.40/month) |
| Rewriter cost (fires on ~1% of requests, ~\$0.0002/call when it does) | ~\$0.0001/day (negligible) | ~\$0.01/day (negligible) |
| **Total** | **~\$0.015/day** | **~\$1.49/day** |

At this corpus size and `gpt-4o-mini` pricing, generation cost scales linearly and stays cheap even at 100x — the real cost driver at scale would be Qdrant hosting and compute for concurrent reranker/embedding calls if the reranker were still in the critical path, which is the other argument (beyond the latency numbers above) for having removed it: a CPU-bound reranker holding a core for ~3.6s per request does not scale the same way a $-metered API call does — it becomes a queuing/throughput problem under concurrent load, not just a per-request cost line.

## Where this leaves Week 8

- **Target met**: p95 latency cut 62%, p50 cut 60%, zero accuracy lost — both qualifying conditions from the brief are satisfied by the latency number alone.
- **Not changed**: embedding model, chunk size, or prompt caching. The corpus is small enough (234 chunks) that a smaller/cheaper index wasn't worth the complexity for the gain available; a repeated-question cache would help most under real deployed traffic, which this local eval can't simulate.
- **Next candidate, not implemented**: cache the dense+sparse embeddings for repeated or near-duplicate questions (e.g. "prerequisites for CS434" asked by many students in the same week) — would cut the now-dominant generation LLM call too, but needs real traffic logs to size a cache correctly rather than guessing.
