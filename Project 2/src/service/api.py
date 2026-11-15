"""service/api.py

FastAPI service exposing the RAG pipeline: POST /ask to get a cited answer,
POST /feedback to record whether it was helpful, GET /health for liveness,
and the static web UI at /.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from generation.pipeline import RagPipeline, build_pipeline

logger = logging.getLogger(__name__)

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
REQUEST_LOG = LOG_DIR / "requests.jsonl"
FEEDBACK_LOG = LOG_DIR / "feedback.jsonl"

app = FastAPI(title="The Librarian", description="RAG over MedTech course syllabi")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline: RagPipeline | None = None


def get_pipeline() -> RagPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="hybrid")


class SourceOut(BaseModel):
    number: int
    header: str
    chunk_id: str
    score: float
    cited: bool


class AskResponse(BaseModel):
    request_id: str
    answer: str
    said_idk: bool
    sources: list[SourceOut]
    rewritten_queries: list[str]
    retrieval_ms: float
    llm_ms: float
    total_ms: float


class FeedbackRequest(BaseModel):
    request_id: str
    helpful: bool
    comment: str | None = None


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    pipeline = get_pipeline()
    try:
        result = pipeline.ask(req.question, mode=req.mode, k=req.k)
    except Exception as exc:
        logger.exception("ask failed for question=%r", req.question)
        raise HTTPException(status_code=500, detail="Internal error answering the question") from exc

    answer = result.answer
    request_id = str(uuid.uuid4())
    sources = [
        SourceOut(
            number=s.number,
            header=s.header or s.chunk_id,
            chunk_id=s.chunk_id,
            score=round(s.score, 4),
            cited=s.number in answer.cited_numbers,
        )
        for s in answer.sources
    ]

    _append_jsonl(
        REQUEST_LOG,
        {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": req.question,
            "rewritten_queries": result.rewritten_queries,
            "mode": req.mode,
            "k": req.k,
            "said_idk": answer.said_idk,
            "retrieved_chunk_ids": result.retrieved_chunk_ids,
            "cited_numbers": answer.cited_numbers,
            "retrieval_ms": result.retrieval_ms,
            "llm_ms": answer.llm_latency_ms,
            "total_ms": result.total_ms,
            "input_tokens": answer.input_tokens,
            "output_tokens": answer.output_tokens,
        },
    )

    return AskResponse(
        request_id=request_id,
        answer=answer.text,
        said_idk=answer.said_idk,
        sources=sources,
        rewritten_queries=result.rewritten_queries,
        retrieval_ms=result.retrieval_ms,
        llm_ms=answer.llm_latency_ms,
        total_ms=result.total_ms,
    )


@app.post("/feedback")
def feedback(req: FeedbackRequest) -> dict:
    _append_jsonl(
        FEEDBACK_LOG,
        {
            "request_id": req.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "helpful": req.helpful,
            "comment": req.comment,
        },
    )
    return {"status": "recorded"}


_static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
