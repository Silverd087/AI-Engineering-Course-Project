"""check_generation.py

Tests the generation step alone. The retrieval hits are hard-coded, so Qdrant is not needed.
"""

from types import SimpleNamespace

from generation.answerer import Answerer
from generation.llm import OpenAIClient


def make_hit(chunk_id: str, text: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        payload={
            "chunk_id": chunk_id,
            "text": text,
            "course_code": "CS434",
            "source_type": "syllabus",
            "semester": "Fall",
            "year": 2026,
        },
    )


HITS = [
    make_hit("doc1::0", "The prerequisite for CS434 is CS280.", 0.91),
    make_hit("doc1::1", "Grading is 40% exams and 60% project.", 0.80),
]

QUESTIONS = [
    "What is the prerequisite for CS434?",   # answerable from HITS
    "What is the late policy for the final project?",  # not in HITS, should get "I don't know"
]

answerer = Answerer(OpenAIClient(model="gpt-4o-mini"), max_chunks=5)

for question in QUESTIONS:
    answer = answerer.answer(question, HITS)
    print("=" * 60)
    print("Q:", question)
    print("A:", answer.text)
    print("cited:", answer.cited_numbers, "| said_idk:", answer.said_idk)
    print(
        "tokens in/out:", answer.input_tokens, answer.output_tokens,
        "| llm ms:", answer.llm_latency_ms,
    )