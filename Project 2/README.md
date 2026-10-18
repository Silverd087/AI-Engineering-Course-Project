# MedTech Librarian

**A retrieval-augmented (RAG) assistant that answers questions about MedTech course syllabi and academic regulations, with a citation for every claim.**

CS496 AI Engineering, Project 2 (Fall 2026), Mediterranean Institute of Technology
Instructor: Dr Abdeldjalil Labed

| | |
|---|---|
| **Live service** | `<URL here>` |
| **Team** | Member A, Member B, Member C (replace with names) |
| **Working version due** | End of Week 7 |
| **Optimised version + demo** | First session of Week 9 |

---

## 1. What this is

Students regularly ask questions such as:

- "What is the late-submission policy in CS496?"
- "Can I retake a failed module, and how many times?"
- "What are the prerequisites for the AI Engineering course?"
- "What do I need to complete before starting my internship?"

The answers are scattered across syllabi, grading policies, exam rules and internship procedures, in different documents and sometimes in different versions. The Librarian searches those documents, answers **only from what it finds**, cites the source passage for each claim, and says **"I don't know"** when nothing relevant is found.

**Users:** MedTech students (our classmates), who tell us when an answer is wrong through the in-app feedback buttons.

### Corpus

| Item | Value |
|---|---|
| Sources | Course syllabi, grading and exam regulations, internship procedures, handbook sections |
| Size | `<N documents / N pages>` (target: several hundred pages) |
| Languages | `<French / English / mixed>` |
| Permission | Written permission from `<administration / instructors>`, stored in `docs/permission/` |
| Personal data | None. Documents are policy and course material only. Student names, grades and IDs are excluded |

> **Note on versions:** some rules differ by cohort or academic year. Every chunk carries `year` and `programme` metadata so the retriever can filter on them.

---

## 2. Quick start

**Setup (one command):**

```bash
make setup
```

This creates a virtual environment, installs dependencies, and downloads the models.

**Run (one command):**

```bash
make run
```

The service starts on `http://localhost:8000`. Ask a question in the web UI, or call the API:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I retake a failed module?"}'
```

**Configuration:** copy `.env.example` to `.env` and fill in the API key for the generation model. Never commit `.env`.

**Rebuild the index from the raw documents:**

```bash
make index
```

**Run the evaluations:**

```bash
make eval-retrieval    # recall@k, latency of the search step
make eval-generation   # faithfulness, correctness, citation accuracy, IDK rate
make ablation          # keyword vs vector vs hybrid vs hybrid + reranker
```

---

## 3. How it works

### Offline: build the index

1. **Load** documents and keep metadata: title, programme, academic year, course code, section.
2. **Chunk** by document structure (headings and sections first, then size limits). Chunk size and overlap are tested, not defaulted. Results are in `design.md`.
3. **Embed** each chunk with a multilingual embedding model and store the vectors.
4. **Keyword index** (BM25) built over the same chunks for hybrid search.

### Online: answer a question

1. **Rewrite** short, vague or multi-part questions into clear search queries.
2. **Retrieve** top-k chunks with keyword + vector search, filtered by metadata (year, programme, course).
3. **Rerank** with a cross-encoder or a small model.
4. **Generate** an answer from the retrieved chunks only, with a citation after each claim.
5. **Abstain** with "I don't know" when retrieval confidence is low or nothing relevant is found.

### Proposed stack (to be confirmed in `design.md`)

| Component | Choice | Justification |
|---|---|---|
| Language | Python 3.11 | Team familiarity, library support |
| Parsing | `pymupdf` / `python-docx` | PDF and Word sources |
| Embeddings | Multilingual sentence embedding model | French / English mixed corpus |
| Vector store | `<FAISS flat file / pgvector / Chroma>` | Corpus is small; justify choice with measurements |
| Keyword search | BM25 (`rank_bm25`) | Exact matches on course codes, article numbers |
| Reranker | Cross-encoder (small) | Tested in the ablation |
| Generation | `<model>` via API | Cost and latency measured per request |
| Service | FastAPI + simple web UI | Needs a URL and a way to ask questions |

---

## 4. Repository layout

```
.
├── README.md
├── design.md              # chunking, index choice, known failure cases
├── optimisation.md        # Week 8 report, before / after numbers
├── postmortem.md          # what went wrong and what we learned
├── Makefile
├── .env.example
├── data/
│   ├── raw/               # source documents (only if permitted to redistribute)
│   ├── processed/         # parsed text and chunks
│   └── eval/              # 100+ questions, answers, source passages
├── src/
│   ├── ingest/            # loading, parsing, chunking
│   ├── index/             # embeddings, vector store, BM25
│   ├── retrieve/          # query rewrite, hybrid search, filters, reranker
│   ├── generate/          # prompts, citations, abstention
│   └── service/           # API, UI, logging, feedback
├── eval/
│   ├── retrieval_eval.py
│   ├── generation_eval.py
│   └── ablation.py
├── docs/
│   └── permission/        # written permission for the corpus
└── report/                # 6-page report
```

---

## 5. Results

> Fill in once the evals have run. Numbers must come from `eval/` scripts on the same test set.

### Retrieval ablation

| Configuration | Recall@5 | Recall@10 | Search latency (p50) |
|---|---|---|---|
| Keyword only (BM25) | | | |
| Vector only | | | |
| Hybrid | | | |
| Hybrid + reranker | | | |

### Generation

| Metric | Result |
|---|---|
| Answer correctness (100+ Q&A pairs) | |
| Faithfulness (every claim supported by a cited chunk) | |
| Citation accuracy | |
| Correct "I don't know" rate | |
| False "I don't know" rate | |

### Service

| Metric | Baseline (Week 7) | Optimised (Week 8) | Change |
|---|---|---|---|
| p50 latency | | | |
| p95 latency | | | |
| Cost per request | | | |
| Accuracy on eval set | | | within 2 points? |

**Cost model:** cost per request today and at 100x the traffic is in `optimisation.md`.

**User feedback:** `<summary of thumbs up/down and comments from real users>`

---

## 6. Known failure cases

Full details are in `design.md`. Expected problem areas:

- **Tables** (grading schemes, credit tables) split across chunks
- **Cross-references** ("see Article 12") pointing to text in another chunk or document
- **Versioning**: the same rule differing between academic years or cohorts
- **Mixed-language** questions and documents
- **Multi-part questions** that need passages from several documents

---

## 7. Team and task breakdown

Three members, same team all term. Each member **owns** one area and **reviews** another, so every member can explain every line.

### Member A: Data and Index

*Owner of: corpus, ingestion, chunking, indexes*

| # | Task | Deliverable | Week |
|---|---|---|---|
| A1 | Choose corpus scope, collect documents, get written permission, check no personal data | `docs/permission/`, `data/raw/` | 5 |
| A2 | Send corpus proposal to the instructor and get approval | Approval by end of Week 5 | 5 |
| A3 | Parse PDFs and Word files, keep metadata (year, programme, course, section) | `src/ingest/` | 5-6 |
| A4 | Implement chunking strategies and test size and overlap | Chunking comparison in `design.md` | 6 |
| A5 | Build the embedding index and BM25 index, justify the store choice | `src/index/`, `make index` | 6 |
| A6 | Write corpus and chunking sections of the report and `design.md` | Report section 1, part of 2 | 7 |
| A7 | Week 8: smaller or cheaper index, fewer or shorter chunks | Numbers in `optimisation.md` | 8 |

### Member B: Retrieval and Generation

*Owner of: search quality, reranking, answers, citations*

| # | Task | Deliverable | Week |
|---|---|---|---|
| B1 | Hybrid search (BM25 + vector) with metadata filters | `src/retrieve/` | 6 |
| B2 | Query rewriting for short, vague and multi-part questions | `src/retrieve/rewrite.py` | 6 |
| B3 | Reranker integration | `src/retrieve/rerank.py` | 6-7 |
| B4 | Generation prompt with per-claim citations, grounded answers only | `src/generate/` | 7 |
| B5 | Abstention logic ("I don't know") with a tuned threshold | `src/generate/abstain.py` | 7 |
| B6 | Write retrieval design and generation sections of the report | Report sections 2-4 (part) | 7 |
| B7 | Week 8: prompt caching, smaller generation model, skip reranker when confident | Numbers in `optimisation.md` | 8 |

### Member C: Evaluation, Service and Optimisation

*Owner of: eval harness, deployment, measurement, cost*

| # | Task | Deliverable | Week |
|---|---|---|---|
| C1 | Define eval format and build the eval harness (reuse the P1 harness) | `eval/`, `data/eval/` schema | 5-6 |
| C2 | Retrieval eval: recall@k and search latency | `eval/retrieval_eval.py` | 6 |
| C3 | Generation eval: correctness, faithfulness, citation accuracy, IDK | `eval/generation_eval.py` | 7 |
| C4 | Ablation script: keyword, vector, hybrid, hybrid + reranker | `eval/ablation.py`, results table | 7 |
| C5 | Build the API and web UI, deploy with a public URL, log requests, add feedback buttons | `src/service/`, live URL | 6-7 |
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
- Eval numbers always come from scripts in `eval/`, run on the same test set.
- Weekly 30-minute sync to check blockers and update this table.

---

## 8. Contributions

> Fill in at the end with what each member actually did, based on the git history and the task table above.

| Member | Contributions |
|---|---|
| Member A | |
| Member B | |
| Member C | |

---

## 9. Grading checklist (from the course brief)

- [ ] Runs from a clean clone with one setup command and one run command
- [ ] Deployed service with a URL
- [ ] 100+ eval questions with answers and source passages in `data/eval/`
- [ ] Retrieval eval, generation eval and ablation scripts in `eval/`
- [ ] `design.md`: chunking, index choice, known failure cases
- [ ] `optimisation.md`: Week 8 before / after numbers (50% cost or p95 cut, at most 2 points of accuracy lost)
- [ ] Cost model, today and at 100x
- [ ] `postmortem.md`, honest about what went wrong
- [ ] Report, max 6 pages
- [ ] No API keys, no personal data
- [ ] Every team member can explain every line

---

## 10. License and data notice

Code: `<license>`. Documents in `data/raw/` belong to MedTech and are used with permission for this course project only.