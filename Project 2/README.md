# MedTech Librarian

**A retrieval-augmented (RAG) assistant that answers questions about MedTech course syllabi and academic regulations, with a citation for every claim.**

CS496 AI Engineering, Project 2 (Fall 2026), Mediterranean Institute of Technology
Instructor: Dr Abdeldjalil Labed

| | |
|---|---|
| **Live service** | `<deployed URL — not yet deployed, runs locally at http://localhost:8000>` |
| **Team** | Farouk, Sara, Sofiene Rouatbi |
| **Working version due** | End of Week 7 |
| **Optimised version + demo** | First session of Week 9 |

---

## 1. What this is

Students regularly ask questions such as:

- "What is the late-submission policy in CS496?"
- "Can I retake a failed module, and how many times?"
- "What are the prerequisites for the AI Engineering course?"
- "What do I need to complete before starting my internship?"

The answers are scattered across syllabi in different documents and sometimes in different versions (e.g. CS434 exists as two different syllabi for Fall 2024 and Fall 2026, with different prerequisites and content). The Librarian searches those documents, answers **only from what it finds**, cites the source chunk for each claim, and says **"I don't know"** when nothing relevant is found.

**Users:** MedTech students asking the kind of questions they'd otherwise dig through a PDF or Word file for. Feedback buttons (👍/👎) on each answer in the web UI log to `data/logs/feedback.jsonl`.

### Corpus

| Item | Value |
|---|---|
| Sources | 42 MedTech course syllabi (`.docx` and `.pdf`) |
| Size | 42 documents, ~295K characters of extracted text, 234 chunks at 384 tokens/64 overlap |
| Languages | English |
| Permission | Internal course material; **the raw syllabi are kept private and are not committed to this repo** (`data/raw/` is gitignored) |
| Personal data | None from students. Instructor/lecturer names appear where the syllabus itself lists them (e.g. "Course Lecturer: Dr. X") — routine public-facing faculty info, not student data |

> **Note on versions:** some courses have multiple syllabi across years (e.g. CS434 Fall 2024 vs Fall 2026). Every chunk carries `course_code`, `year`, and `semester` metadata, and the chunk header makes the course code visible to both keyword and vector search. See `design.md` for how retrieval disambiguates between versions (and where it doesn't).

---

## 2. Quick start

Requires Docker (for Qdrant) and [`uv`](https://docs.astral.sh/uv/). `make` targets use POSIX shell syntax — run them from Git Bash/WSL/macOS/Linux, or translate the underlying commands (shown in `Makefile`) if your shell doesn't support `make`.

**Configuration:** copy `.env.example` to `.env` and fill in `OPENAI_API_KEY`. Never commit `.env`.

**Setup (one command):**

```bash
make setup
```

Installs dependencies with `uv sync` and starts Qdrant via `docker compose up -d qdrant`.

**Build the index from the raw documents** (place your own syllabi in `data/raw/` first — they are not included in this repo):

```bash
make index
```

**Run (one command):**

```bash
make run
```

The service starts on `http://localhost:8000`. Ask a question in the web UI, or call the API:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the prerequisite for CS434?"}'
```

**Run the evaluations:**

```bash
make eval-retrieval    # hit@k, MRR, latency — dense / sparse / hybrid / hybrid+reranker ablation
make eval-generation   # faithfulness, correctness, citation accuracy, IDK rate
make ablation          # same as eval-retrieval (the ablation table is its output)
make test              # unit tests
```

---

## 3. How it works

See `design.md` for the full design rationale, ablation results, and known failure cases. Summary:

### Offline: build the index

1. **Load** documents and extract metadata (course code, title, year, semester) from the filename.
2. **Chunk** at 384 tokens with 64-token overlap (tiktoken), prefixing each chunk with a `course_code - title` header so every chunk is self-identifying for both keyword and vector search.
3. **Embed** each chunk with `BAAI/bge-small-en-v1.5` (dense) and store alongside a BM25-style sparse vector (`Qdrant/bm25`) in the same Qdrant collection.

### Online: answer a question

1. **Rewrite** short, vague, or multi-part questions into one or more standalone search queries (LLM call).
2. **Retrieve** top-k chunks with hybrid (dense + sparse, RRF-fused) search.
3. **Rerank** candidates with a cross-encoder (on by default; see `optimisation.md` for why Week 8 turns it off).
4. **Generate** an answer from the retrieved chunks only, with a `[n]` citation after each claim.
5. **Abstain** with "I don't know" when retrieval finds nothing or the chunks don't support an answer.

### Stack

| Component | Choice | Justification |
|---|---|---|
| Language | Python 3.13 | Team familiarity, library support |
| Parsing | `pymupdf` / `python-docx` | PDF and Word sources |
| Embeddings | `BAAI/bge-small-en-v1.5` | Small, fast, strong on short English passages |
| Vector store | Qdrant (Docker) | Native hybrid (dense+sparse) fusion and payload filtering without extra glue code, at this corpus size |
| Keyword search | BM25 (`Qdrant/bm25`, IDF-weighted) | Exact matches on course codes |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Measured in the ablation — adds latency, not accuracy, on this corpus (see `design.md`) |
| Generation | `gpt-4o-mini` via OpenAI API | Cost/latency measured per request |
| Service | FastAPI + static HTML/JS UI | `/ask`, `/feedback`, `/health` |

---

## 4. Repository layout

```
.
├── README.md
├── design.md               # chunking, index choice, ablation, known failure cases
├── optimisation.md         # Week 8 report, before / after numbers
├── postmortem.md           # what went wrong and what we learned
├── Makefile
├── docker-compose.yml       # Qdrant
├── .env.example
├── data/
│   ├── raw/                # source documents — gitignored, kept private
│   ├── processed/          # manifest.json (metadata only, no document text)
│   ├── eval/               # questions.json: 108 Q&A pairs with source passages
│   └── logs/                # request/feedback logs — gitignored (free-text user input)
├── src/
│   ├── ingest/              # loading, parsing, metadata extraction
│   ├── chunking/            # token-bounded chunker
│   ├── core/                # shared dataclasses (Chunk, Document, ...)
│   ├── indexing/            # Qdrant hybrid repository, index config
│   ├── retrieval/           # hybrid retriever, query rewriter, reranker
│   ├── generation/          # prompts, citations, abstention, LLM client, pipeline
│   ├── orchestrator/        # ingest → chunk → index pipeline
│   └── service/             # FastAPI app + static web UI
└── evaluation/
    ├── evaluate.py          # retrieval eval + ablation (dense/sparse/hybrid/hybrid+reranker)
    ├── generation_eval.py   # faithfulness, citation accuracy, correctness, IDK rate
    ├── metrics.py
    └── results/             # saved eval output (gitignored or regenerated per run)
```

---

## 5. Results

Numbers come from `evaluation/evaluate.py` and `evaluation/generation_eval.py` run against `data/eval/questions.json` (108 questions, 94 answerable / 14 unanswerable). Full discussion in `design.md`.

### Retrieval ablation (hit@k on the 94 answerable questions)

| Configuration | hit@1 | hit@3 | hit@5 | MRR | Search latency (p50) |
|---|---|---|---|---|---|
| Keyword only (BM25) | 0.787 | 0.936 | 0.968 | 0.863 | 11.6ms |
| Vector only | 0.362 | 0.755 | 0.904 | 0.576 | 120.5ms |
| Hybrid | 0.649 | 0.947 | 0.979 | 0.791 | 111.4ms |
| Hybrid + reranker | 0.670 | 0.936 | 0.979 | 0.799 | 3732.8ms |

### Generation (all 108 questions, Week 7 pipeline)

| Metric | Result |
|---|---|
| Answer correctness (vs. reference answer) | 0.977 |
| Faithfulness (every claim supported by a cited chunk) | 0.998 |
| Citation accuracy | 1.000 |
| Correct "I don't know" rate (unanswerable questions) | 1.000 |
| False "I don't know" rate (answerable questions) | 0.064 |

### Service

| Metric | Baseline (Week 7) | Optimised (Week 8) | Change |
|---|---|---|---|
| p50 latency (end to end) | 7144ms | 2829ms | **−60.4%** |
| p95 latency (end to end) | 9791ms | 3687ms | **−62.3%** |
| Generation cost / request | $0.000298 | $0.000296 | −0.7% (flat — see `optimisation.md`) |
| Accuracy on eval set | baseline | +0.012 correctness, +0.002 faithfulness, 0 citation accuracy | no points lost |

Full discussion, methodology, and the 100x cost model are in `optimisation.md`.

**User feedback:** `<summary of thumbs up/down and comments from real users — once deployed>`

---

## 6. Known failure cases

Full details and root causes are in `design.md`. Summary:

- **Reranker latency with no accuracy return** — a generic cross-encoder adds ~3.6s p50 for a sub-1-point accuracy change on this corpus (addressed in Week 8).
- **Occasional false abstention from LLM non-determinism** — the same question through the same pipeline can answer correctly or say "I don't know" on different calls, even at temperature=0.
- **Multi-version documents** (e.g. two CS434 syllabi across years) are resolved by chunk metadata, but a question without a year is inherently ambiguous.
- **No conversation memory** — a vague follow-up with no prior turn to resolve against gets a generic, unfocused answer rather than a correct abstention or clarifying question.
- **PDF table extraction isn't attempted** — relies on PyMuPDF's plain-text mode happening to preserve table content inline.
- **Chunking tables alongside prose** dilutes per-chunk semantic focus for dense retrieval (hybrid search absorbs most of this via BM25).
- **Cross-references / prerequisite chains** are not resolved transitively — one retrieval hop only.

---

## 7. Team and task breakdown

Three members, same team all term. Each member **owns** one area and **reviews** another, so every member can explain every line.

### Member A: Data and Index

*Owner of: corpus, ingestion, chunking, indexes*

| # | Task | Deliverable | Week |
|---|---|---|---|
| A1 | Choose corpus scope, collect documents, check no personal data | `data/raw/` (kept private, not in git) | 5 |
| A2 | Send corpus proposal to the instructor and get approval | Approval by end of Week 5 | 5 |
| A3 | Parse PDFs and Word files, keep metadata (year, programme, course, section) | `src/ingest/` | 5-6 |
| A4 | Implement chunking strategies and test size and overlap | Chunking comparison in `design.md` | 6 |
| A5 | Build the embedding index and BM25 index, justify the store choice | `src/indexing/`, `make index` | 6 |
| A6 | Write corpus and chunking sections of the report and `design.md` | Report section 1, part of 2 | 7 |
| A7 | Week 8: smaller or cheaper index, fewer or shorter chunks | Numbers in `optimisation.md` | 8 |

### Member B: Retrieval and Generation

*Owner of: search quality, reranking, answers, citations*

| # | Task | Deliverable | Week |
|---|---|---|---|
| B1 | Hybrid search (BM25 + vector) with metadata filters | `src/retrieval/retriever.py` | 6 |
| B2 | Query rewriting for short, vague and multi-part questions | `src/retrieval/query_rewriter.py` | 6 |
| B3 | Reranker integration | `src/retrieval/reranker.py` | 6-7 |
| B4 | Generation prompt with per-claim citations, grounded answers only | `src/generation/` | 7 |
| B5 | Abstention logic ("I don't know") when nothing relevant is retrieved | `src/generation/answerer.py` | 7 |
| B6 | Write retrieval design and generation sections of the report | Report sections 2-4 (part) | 7 |
| B7 | Week 8: prompt caching, smaller generation model, skip reranker when confident | Numbers in `optimisation.md` | 8 |

### Member C: Evaluation, Service and Optimisation

*Owner of: eval harness, deployment, measurement, cost*

| # | Task | Deliverable | Week |
|---|---|---|---|
| C1 | Define eval format and build the eval harness (reuse the P1 harness) | `evaluation/`, `data/eval/` schema | 5-6 |
| C2 | Retrieval eval: hit@k and search latency | `evaluation/evaluate.py` | 6 |
| C3 | Generation eval: correctness, faithfulness, citation accuracy, IDK | `evaluation/generation_eval.py` | 7 |
| C4 | Ablation: keyword, vector, hybrid, hybrid + reranker | `evaluation/evaluate.py` (same script, multi-mode) | 7 |
| C5 | Build the API and web UI, deploy with a public URL, log requests, add feedback buttons | `src/service/` done locally; public URL still pending | 6-7 |
| C6 | Cost model today and at 100x, p50 / p95 latency tracking | `optimisation.md` | 7-8 |
| C7 | Week 8: lead the before / after measurement on the same test set, caching of repeated questions | `optimisation.md` | 8 |

### Shared by everyone

| Task | Detail | Week |
|---|---|---|
| Eval questions | Each member writes **35+** question-answer pairs, each with the source passage. Total **100+**. Include unanswerable questions to test "I don't know" | 5-6 |
| Cross-review | A reviews B, B reviews C, C reviews A. Every pull request needs one review | 5-8 |
| Known failure cases | Each member documents failures found in their own area | 7-8 |
| README, report, postmortem | Final assembly and the Contributions section | 8-9 |
| Demo | All three present and answer questions on any part of the code | 9 |

### Timeline

| Week | Goal |
|---|---|
| **5** | Corpus chosen and approved, permission obtained, eval format agreed, 30+ questions drafted |
| **6** | Ingestion, chunking and indexes working; hybrid search and eval harness running; 100+ questions done |
| **7** | Reranker, generation with citations and abstention, deployed service, full eval and ablation. **Working version delivered** |
| **8** | Optimise: cut cost or p95 latency by 50% with at most 2 points of accuracy lost. Write `optimisation.md` |
| **9** | Final report, postmortem, demo (first session) |

### Ground rules

- One branch per task, pull requests with one review before merging to `main`.
- No API keys and no personal data in the repo, ever.
- Eval numbers always come from scripts in `evaluation/`, run on the same test set.
- Weekly 30-minute sync to check blockers and update this table.

---

## 8. Contributions

> Fill in at the end with what each member actually did, based on the git history and the task table above.

| Member | Contributions |
|---|---|
| Farouk | |
| Sara | |
| Sofiene Rouatbi | |

---

## 9. Grading checklist (from the course brief)

- [x] Runs from a clean clone with one setup command and one run command (`make setup`, `make run` — needs Docker + `uv`; raw syllabi must be supplied separately, see §1)
- [ ] Deployed service with a URL (works locally at `http://localhost:8000`; public deployment pending a hosting decision)
- [x] 100+ eval questions with answers and source passages in `data/eval/` (108, verified against real chunk content)
- [x] Retrieval eval, generation eval and ablation scripts in `evaluation/`
- [x] `design.md`: chunking, index choice, known failure cases
- [x] `optimisation.md`: Week 8 before / after numbers (p95 latency cut 62.3%, accuracy improved rather than lost)
- [x] Cost model, today and at 100x
- [x] `postmortem.md`, honest about what went wrong
- [ ] Report, max 6 pages
- [x] No API keys, no personal data (raw syllabi, logs, and vector store kept out of git)
- [ ] Every team member can explain every line

---

## 10. License and data notice

Code: `<license>`. Documents in `data/raw/` belong to MedTech, are used for this course project only, and are deliberately **not committed to this repository** — the team keeps the source syllabi private. A clean clone needs its own copy of the raw files in `data/raw/` before running `make index`.