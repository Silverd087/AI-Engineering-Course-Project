# Design

## 1. Corpus and users

**Corpus**: 42 MedTech course syllabi (`.docx` and `.pdf`), covering CS, ECE, MATH, PHYS, CHEM, ECO, GOV, COM, ME, RE and general-education courses, Fall 2023–2026. Each syllabus includes prerequisites, learning outcomes, course content, grading, Gen AI policy, instructor/schedule tables, and a continuous-improvement history.

**Users**: MedTech students asking the kind of questions they'd otherwise dig through a PDF for — "What's the prerequisite for CS434?", "How is CS429 graded?", "Does ECE360 allow generative AI tools?" — plus a few cross-course and "is this even in scope" questions to exercise abstention.

**Permission / privacy**: the raw syllabi (`data/raw/`) are kept out of version control (`.gitignore`) at the team's request — they are not publicly redistributable. The eval set (`data/eval/questions.json`) only carries short (one-to-two-line) quoted excerpts as source passages, not full documents. No student data appears anywhere in the corpus; the service does surface instructor names (e.g. "Course Lecturer: Dr. X"), which is routine public-facing faculty information already in the official syllabi, not student PII.

## 2. Pipeline design

### Offline: ingestion → chunking → indexing

- **Parsing**: `python-docx` for `.docx`, `pymupdf` for `.pdf` (`src/ingest/`). Metadata (course code, title, year, semester, source type) is extracted from the filename via `MetadataExtractor`.
- **Chunking** (`src/chunking/chunker.py`): token-bounded (tiktoken `cl100k_base`), paragraph-aware splitting at **384 tokens with 64-token overlap**. Every chunk is prefixed with a `course_code - title` header before embedding — see "What we found and fixed" below for why.
- **Embedding + index**: Qdrant, storing a dense vector (`BAAI/bge-small-en-v1.5`, 384-dim) and a sparse BM25-style vector (`Qdrant/bm25`, IDF-weighted) per chunk in one collection, fused at query time with Reciprocal Rank Fusion (RRF). Chosen over a flat file or pgvector because Qdrant gives native hybrid fusion and payload filtering out of the box at this corpus size (234 chunks) without extra glue code.
- **Metadata filtering**: payload-indexed on `course_code`, `year`, `semester`, `source_type`, etc., so retrieval can be scoped (e.g. to a specific year) — plumbed through but not yet exposed in the UI.

### Online: question → answer

1. **Query rewrite** (`src/retrieval/query_rewriter.py`): an LLM call turns short/vague/multi-part questions into one or more standalone search queries. A multi-part question like "What are the prerequisites for CS495 and CS441?" splits into two queries, each retrieved separately and merged by chunk ID (keeping the best score per chunk). As of Week 8, a cheap heuristic (`needs_rewrite`) skips this LLM call entirely for questions that are already clear and single-topic (99% of the eval set) — see `optimisation.md`.
2. **Hybrid retrieval** (`src/retrieval/retriever.py` + `src/indexing/repository.py`): dense + sparse search fused via RRF, `k` configurable per call.
3. **Reranking** (`src/retrieval/reranker.py`): a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) reorders a wider candidate pool (15) down to `k`. See the ablation below — this is on by default for the Week 7 version but is the first thing cut in Week 8.
4. **Generation** (`src/generation/`): the LLM (`gpt-4o-mini`) answers strictly from the numbered retrieved chunks, citing `[n]` per claim, and must reply with an exact "I don't know" string when nothing relevant is retrieved or the chunks don't support an answer.
5. **Abstention**: enforced two ways — the answerer never calls the LLM at all if retrieval returns nothing, and the system prompt instructs the model to abstain when the chunks don't contain the answer.

### Service

FastAPI (`src/service/api.py`) exposing `POST /ask`, `POST /feedback`, `GET /health`, and a static HTML/JS page at `/`. Every request is logged to `data/logs/requests.jsonl` (question, rewritten queries, retrieved chunk IDs, citations, latency, token counts) and feedback to `data/logs/feedback.jsonl` — both gitignored since free-text student questions could contain personal data.

## 3. Retrieval results and ablation

Measured with `evaluation/evaluate.py` against the 94 answerable questions in `data/eval/questions.json` (hit@k = correct chunk present in top k; MRR = mean reciprocal rank).

| Configuration | hit@1 | hit@3 | hit@5 | MRR | p50 latency | p95 latency |
|---|---|---|---|---|---|---|
| Keyword only (BM25) | 0.787 | 0.936 | 0.968 | 0.863 | 11.6ms | 31.5ms |
| Vector only (dense) | 0.362 | 0.755 | 0.904 | 0.576 | 120.5ms | 162.6ms |
| Hybrid (RRF) | 0.649 | 0.947 | 0.979 | 0.791 | 111.4ms | 189.3ms |
| Hybrid + reranker | 0.670 | 0.936 | 0.979 | 0.799 | 3732.8ms | 4163.1ms |

**What the ablation shows:**
- BM25 alone is surprisingly strong on this corpus (hit@1 = 0.787) because most questions reference an exact, distinctive token: a course code. Dense embeddings alone do worse at rank 1 (0.362) because many chunks share near-identical generic syllabus boilerplate ("This course is a single subject course at the South Mediterranean University...") that dense similarity doesn't distinguish well.
- Hybrid fusion trades a little top-1 precision for much better recall at 3–5 and a large recall lift over dense alone — the right tradeoff for a system that retrieves `k=5` and only cites what it finds.
- The reranker **does not pay for itself here**: +0.021 hit@1, essentially flat hit@5/MRR, for **~3.6 extra seconds per query** (CPU cross-encoder inference over 15 candidates). This is real, measured evidence — not a guess — that a generic, non-domain-tuned reranker adds negligible value once hybrid search is already strong, and it directly motivates the Week 8 decision in `optimisation.md`.

## 4. Generation results

Measured with `evaluation/generation_eval.py` (LLM-as-judge, `gpt-4o-mini`) against all 108 questions (94 answerable, 14 deliberately unanswerable), using the Week 7 pipeline (hybrid + reranker + rewriter):

| Metric | Result |
|---|---|
| Faithfulness (claims supported by a cited chunk) | 0.998 |
| Citation accuracy (cited chunk actually supports the claim) | 1.000 |
| Answer correctness (vs. reference answer) | 0.977 |
| Correct "I don't know" rate (on unanswerable questions) | 1.000 |
| False "I don't know" rate (on answerable questions) | 0.064 |

Retrieval and generation are measured separately by design: a wrong citation on a right-sounding answer would show up as a faithfulness/citation-accuracy failure even if the final text reads fine.

## 5. What we found and fixed (not in the original plan)

Running the pipeline end-to-end — not just reading the code — surfaced five real bugs, in order of how much they mattered:

1. **Tables were extracted but never merged into the document text** (`src/ingest/word_parser.py`). `python-docx` table extraction built a `tables_text` list but the parser only ever joined paragraph text into `full_text`. Since grading breakdowns, schedules, and instructor info live in Word tables for most syllabi, this meant **~38 of 42 courses had their real grading percentages completely unsearchable** — the RAG system could never have answered "what's the grade breakdown for X" correctly for most courses. Fixing this nearly doubled total corpus text (174K → 295K characters) and chunk count (131 → 234).
2. **Chunks never contained their own course code.** 81 of 98 chunks with a known `course_code` never mentioned that code in the chunk's own text (it only lived in metadata), so a query like "prerequisites for CS495" had nothing lexical or semantic to anchor on in most chunks. Fixed by prepending a `course_code - title` header to every chunk. This alone took hybrid hit@5 from 0.563 to 0.989 on an earlier (pre-table-fix) version of the eval set.
3. **`MetadataExtractor.COURSE_CODE_PATTERN`** only matched 2–3 letter department prefixes anchored to a hyphen-split filename part, silently dropping `course_code` for all MATH/PHYS/CHEM courses (4-letter prefixes) and any file with an inconsistent space/hyphen (`"CS434 -SYLLABUS-F24.docx"`) — 11 of 42 documents. Fixed with a regex matched against the raw filename stem instead of a hyphen-split token.
4. **`IngestionOrchestrator._stage_indexing()` never called `repository.init_schema()`.** Every indexing run failed with "Collection does not exist" — silently, because `skip_errors=True` swallowed the exception and reported "pipeline complete" with 0 chunks indexed.
5. **`HybridRetriever.retrieve()` passed a `query_filter` kwarg that `QdrantHybridRepository.search()` didn't accept**, so any call through the main `RagPipeline` crashed outright, even with no filter set.

None of these were visible from reading the code in isolation — they only surfaced by actually running ingestion → indexing → retrieval → generation against a live Qdrant instance and checking the numbers moved the way they should.

## 6. Known failure cases

- **Reranker latency with no accuracy return.** A generic cross-encoder (MS MARCO-trained, not domain-tuned) adds ~3.6s p50 for a sub-1-point accuracy change on this corpus. Addressed in `optimisation.md`.
- **Occasional false abstention from LLM non-determinism.** Even at `temperature=0`, the same question with identical retrieved context sometimes gets a correct answer and sometimes "I don't know" (confirmed by calling the pipeline 4 times on the same question: 2/4 answered correctly, 2/4 abstained). This is a known property of hosted LLM inference (batching/routing non-determinism), not a bug in this codebase, and shows up as the 6.4% false-IDK rate above.
- **Multi-version documents.** The corpus has two CS434 syllabi (Fall 2024 "data mining" version and Fall 2026 "data science" version) with different prerequisites and content. The system resolves this correctly today only because chunk headers carry the year/semester and the generation prompt is instructed to cite precisely — but a question that doesn't specify a year is inherently ambiguous and the system picks whichever version retrieval ranks highest.
- **No conversation memory.** A deliberately vague follow-up question ("what about its prereqs?") with no prior turn to resolve "its" against gets rewritten into a generic standalone query and answered with a plausible-but-unfocused mix of several courses' prerequisites — correct behavior for a single-turn system, but a real limitation for a natural chat flow.
- **PDF table extraction is not attempted** (`src/ingest/pdf_parser.py` hardcodes `tables=[]`); the 2 PDF-based syllabi (CS429, CS434 Fall 2026) rely on PyMuPDF's plain-text extraction happening to preserve table cell text inline, which it does for these two documents, but this isn't a guaranteed property of arbitrary PDF tables.
- **Chunking tables alongside prose dilutes per-chunk semantic focus.** After merging table text into chunks, dense-only retrieval precision dropped at rank 1 (table rows and schedule data pull a chunk's embedding away from a clean "prerequisites" or "content" topic). Hybrid search absorbs most of this via BM25's exact-match strength, but a future improvement would chunk tables as separate, labeled units rather than appending them to the preceding prose chunk.
- **Cross-references** ("see Article 12", prerequisite chains like CS420 → CS341 → CS101) are not resolved transitively — the system answers from the directly retrieved chunk only, so a question like "what do I need before CS420's prerequisite?" would need two retrieval hops it doesn't currently make.
