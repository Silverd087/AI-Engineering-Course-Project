from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IDK_PHRASE = "I don't know based on the provided documents."

SYSTEM_PROMPT = f"""You answer questions about university course documents.

Rules:
- Use only the numbered context chunks. Do not use outside knowledge.
- After each claim, cite the chunk it comes from, like [2]. Cite only chunk numbers that appear in the context.
- If the chunks do not contain the answer, reply with exactly: {IDK_PHRASE}
- Do not guess dates, grades, credits or course codes that are not in the chunks."""


@dataclass(frozen=True)
class Source:
    number: int
    chunk_id: str
    text: str
    header: str
    score: float
    source_path: str


def _header(payload: dict[str, Any]) -> str:
    """Short human-readable label for a chunk, e.g. 'CS434, syllabus, Fall 2026'."""
    parts = [
        payload.get("course_code"),
        payload.get("source_type"),
        " ".join(str(p) for p in (payload.get("semester"), payload.get("year")) if p),
        payload.get("section"),
    ]
    return ", ".join(str(p) for p in parts if p)


def build_sources(hits: list[Any], max_chunks: int) -> list[Source]:
    """Turn retrieval hits (Qdrant ScoredPoint objects) into numbered sources."""
    sources = []
    for number, hit in enumerate(hits[:max_chunks], start=1):
        payload = hit.payload or {}
        sources.append(
            Source(
                number=number,
                chunk_id=payload.get("chunk_id", ""),
                text=payload.get("text", ""),
                header=_header(payload),
                score=float(hit.score),
                source_path=payload.get("source_path", ""),
            )
        )
    return sources


def build_messages(question: str, sources: list[Source]) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"[{s.number}] ({s.header})\n{s.text}" for s in sources
    )
    user_content = f"Context:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]