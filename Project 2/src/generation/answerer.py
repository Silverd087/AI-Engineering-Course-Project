from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from generation.llm import LLMClient
from generation.prompt import IDK_PHRASE, Source, build_messages, build_sources

_CITATION = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class Answer:
    question: str
    text: str
    sources: list[Source]
    cited_numbers: list[int]
    said_idk: bool
    input_tokens: int
    output_tokens: int
    llm_latency_ms: float


class Answerer:
    def __init__(self, llm: LLMClient, max_chunks: int = 5) -> None:
        self.llm = llm
        self.max_chunks = max_chunks

    def answer(self, question: str, hits: list[Any]) -> Answer:
        sources = build_sources(hits, self.max_chunks)

        # No retrieved context means no answer. Skip the LLM call entirely.
        if not sources:
            return Answer(
                question=question,
                text=IDK_PHRASE,
                sources=[],
                cited_numbers=[],
                said_idk=True,
                input_tokens=0,
                output_tokens=0,
                llm_latency_ms=0.0,
            )

        messages = build_messages(question, sources)

        start = time.perf_counter()
        response = self.llm.chat(messages)
        llm_latency_ms = (time.perf_counter() - start) * 1000

        text = response.text.strip()
        valid_numbers = {s.number for s in sources}
        cited = sorted(
            {int(n) for n in _CITATION.findall(text) if int(n) in valid_numbers}
        )

        return Answer(
            question=question,
            text=text,
            sources=sources,
            cited_numbers=cited,
            said_idk=IDK_PHRASE.lower() in text.lower(),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            llm_latency_ms=round(llm_latency_ms, 2),
        )