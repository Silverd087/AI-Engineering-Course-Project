from __future__ import annotations

import json
from collections.abc import Callable

JUDGE_PROMPT = """You are checking an answer produced from numbered context chunks.

Question: {question}

Answer:
{answer}

Context chunks:
{context}

Split the answer into individual claims. For each claim return:
- "claim": the claim text
- "cited_chunk": the chunk number the answer cites for it, or null if none
- "supported": true only if that chunk states the claim explicitly

Return only a JSON list of objects with these three keys."""


def build_context(chunks: list[dict]) -> str:
    """chunks: list of {"chunk_id": str, "text": str}. Numbered from 1."""
    return "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks, start=1))


def _parse_judge_output(raw: str) -> list[dict]:
    """Strip markdown code fences if the judge added them, then parse the JSON list."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


def judge_answer(
    question: str,
    answer: str,
    chunks: list[dict],
    judge: Callable[[str], str],
) -> list[dict]:
    """Return the judge's claim list. `judge` takes a prompt string and returns the model's text."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        context=build_context(chunks),
    )
    return _parse_judge_output(judge(prompt))


def faithfulness(claims: list[dict]) -> float:
    """Share of claims marked supported. An answer with no claims scores 0."""
    if not claims:
        return 0.0
    return sum(1 for c in claims if c["supported"]) / len(claims)


def citation_accuracy(claims: list[dict]) -> float:
    """Share of cited claims that the cited chunk actually supports."""
    cited = [c for c in claims if c.get("cited_chunk") is not None]
    if not cited:
        return 0.0
    return sum(1 for c in cited if c["supported"]) / len(cited)


def idk_rate(rows: list[dict]) -> float:
    """Among unanswerable questions, the share where the system said it doesn't know.

    Each row needs "answerable" (bool) and "said_idk" (bool). Set said_idk by checking
    the answer by hand or with the judge, not with a keyword match alone.
    """
    unanswerable = [r for r in rows if not r["answerable"]]
    if not unanswerable:
        return 0.0
    return sum(1 for r in unanswerable if r["said_idk"]) / len(unanswerable)