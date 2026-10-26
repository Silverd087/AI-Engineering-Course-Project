"""chunking/chunker.py"""

from __future__ import annotations

import re
from typing import Iterator

import tiktoken

from core.models import Chunk, Document


class DocumentChunker:
    """Splits Documents into token-bounded Chunks respecting structural boundaries."""

    def __init__(
        self,
        chunk_size: int = 384,
        chunk_overlap: int = 64,
        tokenizer_name: str = "cl100k_base",
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)

    def _split_units(self, text: str) -> list[str]:
        parts = re.split(r"(\n{2,}|\n)", text)
        units: list[str] = []
        buf = ""
        for p in parts:
            if not p:
                continue
            if p.isspace():
                buf += p
            else:
                if buf:
                    units.append(buf)
                    buf = ""
                units.append(p)
        if buf:
            units.append(buf)
        return units

    def split_document(self, doc: Document) -> Iterator[Chunk]:
        units = self._split_units(doc.text)
        current_tokens: list[int] = []
        current_text = ""
        chunk_idx = 0

        for unit in units:
            unit_tokens = self.tokenizer.encode(unit)

            if len(current_tokens) + len(unit_tokens) > self.chunk_size:
                if current_tokens:
                    yield Chunk(
                        chunk_id=f"{doc.doc_id}::{chunk_idx}",
                        text=current_text.strip(),
                        metadata={**doc.metadata, "doc_id": doc.doc_id, "chunk_index": chunk_idx},
                    )
                    chunk_idx += 1
                    overlap_tokens = current_tokens[-self.chunk_overlap :]
                    current_text = self.tokenizer.decode(overlap_tokens)
                    current_tokens = list(overlap_tokens)

            current_tokens.extend(unit_tokens)
            current_text += unit

        if current_tokens and current_text.strip():
            yield Chunk(
                chunk_id=f"{doc.doc_id}::{chunk_idx}",
                text=current_text.strip(),
                metadata={**doc.metadata, "doc_id": doc.doc_id, "chunk_index": chunk_idx},
            )

    def split_all(self, docs: Iterator[Document]) -> Iterator[Chunk]:
        for doc in docs:
            yield from self.split_document(doc)