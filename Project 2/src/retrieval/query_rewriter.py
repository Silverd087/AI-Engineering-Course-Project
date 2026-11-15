"""retrieval/query_rewriter.py"""

from __future__ import annotations

import re

from generation.llm import LLMClient

_COURSE_CODE = re.compile(r"\b[A-Z]{2,4}\d{3,}\b")
_VAGUE_MARKERS = {"it", "its", "that", "this", "they", "them"}


def needs_rewrite(question: str) -> bool:
    """Cheap heuristic to skip the rewrite LLM call for questions that are already
    clear and single-topic — this is most requests in practice. Errs toward calling
    the rewriter when unsure, since a spurious rewrite call is cheap and a skipped
    one that was actually needed costs retrieval quality."""
    codes = set(_COURSE_CODE.findall(question.upper()))
    if len(codes) >= 2:
        return True  # names multiple courses -> likely needs splitting
    words = question.strip().split()
    if len(words) < 4:
        return True  # too short/terse to trust as self-contained
    if any(w.strip("?.,!'\"").lower() in _VAGUE_MARKERS for w in words):
        return True  # pronoun reference needs resolving
    if " and " in question.lower() and not codes:
        return True  # possible multi-part question without an explicit course code
    return False


SYSTEM_PROMPT = """You turn a student's question into one or more clear search queries \
for a university course-document search engine (syllabi, prerequisites, grading, policies).

Rules:
- If the question is already specific and self-contained, return it unchanged.
- If it is short, vague, or depends on earlier context, rewrite it into a standalone \
query that names the actual subject (course code, policy, etc).
- If it asks about more than one course or more than one topic, split it into separate \
focused queries, one per line.
- Keep course codes and proper nouns exactly as given. Do not answer the question.
- Output only the query or queries, one per line. No numbering, no extra text."""


class QueryRewriter:
    """Expands a raw question into one or more search queries via an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def rewrite(self, question: str) -> list[str]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = self.llm.chat(messages)
        queries = [line.strip() for line in response.text.strip().splitlines() if line.strip()]
        return queries or [question]
