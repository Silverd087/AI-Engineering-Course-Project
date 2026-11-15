# Postmortem

## What went wrong

**The pipeline looked done but had never actually run end-to-end.** Before this pass, the repo had hybrid retrieval, a reranker-shaped ablation script, and a generation pipeline with citation enforcement — all individually well-written. But nobody had run ingestion → indexing → retrieval → generation together against a live Qdrant instance and checked that the numbers moved the way they should. Five real bugs were hiding in that gap:

- `HybridRetriever.retrieve()` passed a `query_filter` keyword that `QdrantHybridRepository.search()` didn't accept, so the main `RagPipeline.ask()` crashed on every call, even with no filter set.
- `IngestionOrchestrator._stage_indexing()` never called `repository.init_schema()`. Every indexing run failed with "Collection does not exist" — and because `skip_errors=True` caught the exception, the pipeline printed "complete" with 0 chunks indexed instead of failing loudly.
- The filename-based course-code regex silently dropped `course_code` for 11 of 42 documents (every MATH/PHYS/CHEM course, since the pattern only matched 2–3 letter prefixes).
- 81 of 98 chunks never mentioned their own course code in the chunk text, so the single most common query shape ("prerequisites for CS495") had almost nothing to match on.
- **The big one**: `.docx` table extraction built a `tables_text` list but the parser never joined it into the document's `full_text`. Grading breakdowns, schedules, and instructor info live in tables for most syllabi — so roughly 38 of 42 courses had their actual grading percentages completely unsearchable. The system could pass every retrieval metric and still be structurally unable to answer one of the most obvious question categories for this corpus.

None of these were visible from a code review. They only surfaced by actually indexing the corpus, running the ablation, and noticing the numbers were suspiciously low or the service crashed — then tracing each failure back to its cause.

**The reranker didn't pay for itself, and we almost shipped it anyway.** It's a reasonable default to assume "reranker = more accurate," and the brief suggests it as a required pipeline stage. Measured, a generic MS MARCO-trained cross-encoder added ~3.6 seconds of p50 latency for a sub-one-point accuracy change once hybrid search was already strong (post table-fix). Without running the ablation with real latency numbers, this would have shipped as "the better option" by assumption rather than evidence.

**LLM non-determinism caused silent, hard-to-reproduce false abstentions.** Calling the exact same question through the exact same pipeline 4 times in a row produced "I don't know" twice and a correct, cited answer twice — at `temperature=0`, with identical retrieved context. This is a known property of hosted LLM inference, not something fixable in this codebase, but it means a single manual test of a question ("it worked when I tried it") is not sufficient evidence that the system handles that question reliably. The eval set's false-IDK rate (6.4%) is a more honest measure than any one spot-check.

## What we'd do differently

- **Run the full pipeline against real infrastructure before trusting unit-level correctness.** Each module (chunker, repository, retriever, answerer) worked fine in isolation; the integration gaps between them were where the real damage was.
- **Build the eval set from real parsed content, not from what the corpus is "supposed to" contain.** Several early draft eval questions assumed grading percentages existed in plain text before the table-merge bug was found — the eval set itself would have quietly baked in the same blind spot as the system if it hadn't been built by reading actual chunk dumps.
- **Treat "adds a standard RAG component" as a hypothesis to test, not a default to ship.** The reranker, in particular, needed a real head-to-head ablation with latency numbers before being trusted as an improvement.
- **Decide corpus privacy boundaries explicitly, in writing, before building on top of them.** The raw syllabi needed to stay private per team policy; this should be a `.gitignore` decision made deliberately at the start, not discovered as an uncommitted, unexplained change partway through.

## What's still open

- Public deployment with a URL (local FastAPI service is fully working and tested; hosting platform/credentials are a team decision).
- PDF table extraction (`pdf_parser.py` hardcodes `tables=[]`) — the 2 PDF syllabi happen to work because PyMuPDF's plain-text mode preserves table content inline, but that's not guaranteed for all PDFs.
- A chunking refinement that keeps table rows as separate, labeled chunks instead of appending them to the preceding prose chunk, to recover the dense-retrieval precision that dropped slightly after the table-merge fix.
- Multi-hop prerequisite chains (e.g. "what do I need before CS420's prerequisite?") are not resolved — the system answers from one retrieval hop only.
