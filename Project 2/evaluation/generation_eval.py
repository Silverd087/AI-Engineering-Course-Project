from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

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

CORRECTNESS_PROMPT = """You are grading whether a generated answer correctly answers a question,
compared to a reference answer. Ignore wording, citation markers like [1], and extra detail that
does not contradict the reference.

Question: {question}

Reference answer: {reference}

Generated answer: {answer}

Return only a JSON object: {{"correct": true or false, "reason": "<one sentence>"}}"""


def build_context(chunks: list[dict]) -> str:
    """chunks: list of {"chunk_id": str, "text": str}. Numbered from 1."""
    return "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks, start=1))


def _parse_json(raw: str):
    """Strip markdown code fences if the judge added them, then parse JSON."""
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
    return _parse_json(judge(prompt))


def judge_correctness(
    question: str,
    answer: str,
    reference: str,
    judge: Callable[[str], str],
) -> dict:
    prompt = CORRECTNESS_PROMPT.format(question=question, reference=reference, answer=answer)
    return _parse_json(judge(prompt))


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


def false_idk_rate(rows: list[dict]) -> float:
    """Among answerable questions, the share where the system wrongly said it doesn't know."""
    answerable = [r for r in rows if r["answerable"]]
    if not answerable:
        return 0.0
    return sum(1 for r in answerable if r["said_idk"]) / len(answerable)


def correctness_rate(rows: list[dict]) -> float:
    """Share of answerable, non-abstained questions the correctness judge marked correct."""
    scored = [r for r in rows if r.get("correct") is not None]
    if not scored:
        return 0.0
    return sum(1 for r in scored if r["correct"]) / len(scored)


def summarize(rows: list[dict]) -> dict:
    faithfulness_scores = [r["faithfulness"] for r in rows if r["faithfulness"] is not None]
    citation_scores = [r["citation_accuracy"] for r in rows if r["citation_accuracy"] is not None]
    return {
        "num_questions": len(rows),
        "faithfulness": round(sum(faithfulness_scores) / len(faithfulness_scores), 3) if faithfulness_scores else None,
        "citation_accuracy": round(sum(citation_scores) / len(citation_scores), 3) if citation_scores else None,
        "correctness": round(correctness_rate(rows), 3),
        "idk_rate_on_unanswerable": round(idk_rate(rows), 3),
        "false_idk_rate_on_answerable": round(false_idk_rate(rows), 3),
    }


def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    from generation.llm import OpenAIClient
    from generation.pipeline import build_pipeline

    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("data/eval/questions.json"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--model", default="gpt-4o-mini", help="Generation model")
    parser.add_argument("--judge-model", default="gpt-4o-mini", help="LLM-judge model")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--no-reranker", action="store_true")
    parser.add_argument("--no-rewriter", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N questions")
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[: args.limit]

    pipeline = build_pipeline(
        qdrant_url=args.qdrant_url,
        model=args.model,
        max_chunks=args.k,
        use_reranker=not args.no_reranker,
        use_rewriter=not args.no_rewriter,
    )
    judge_llm = OpenAIClient(model=args.judge_model)

    def judge(prompt: str) -> str:
        return judge_llm.chat([{"role": "user", "content": prompt}]).text

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['question']}", flush=True)
        result = pipeline.ask(q["question"], k=args.k)
        answer = result.answer
        row = {
            "question": q["question"],
            "answerable": q.get("answerable", True),
            "answer": answer.text,
            "said_idk": answer.said_idk,
            "retrieval_ms": result.retrieval_ms,
            "llm_ms": answer.llm_latency_ms,
            "total_ms": result.total_ms,
            "input_tokens": answer.input_tokens,
            "output_tokens": answer.output_tokens,
            "faithfulness": None,
            "citation_accuracy": None,
            "correct": None,
        }

        if q.get("answerable", True) and not answer.said_idk:
            chunks = [{"chunk_id": s.chunk_id, "text": s.text} for s in answer.sources]
            try:
                claims = judge_answer(q["question"], answer.text, chunks, judge)
                row["faithfulness"] = faithfulness(claims)
                row["citation_accuracy"] = citation_accuracy(claims)
                row["claims"] = claims
            except Exception as exc:
                row["judge_error"] = str(exc)

            if q.get("answer"):
                try:
                    verdict = judge_correctness(q["question"], answer.text, q["answer"], judge)
                    row["correct"] = bool(verdict.get("correct"))
                    row["correctness_reason"] = verdict.get("reason")
                except Exception as exc:
                    row["correctness_judge_error"] = str(exc)

        rows.append(row)

        if i % 10 == 0 or i == len(questions):
            (args.out / "generation.json").write_text(
                json.dumps({"summary": summarize(rows), "rows": rows}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    summary = summarize(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
