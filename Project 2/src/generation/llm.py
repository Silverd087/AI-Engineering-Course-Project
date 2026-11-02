from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    def chat(self, messages: list[dict[str, str]]) -> LLMResponse: ...


class OpenAIClient:
    """Calls the OpenAI Chat Completions API. Reads OPENAI_API_KEY from the environment."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 600,
        timeout_s: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Check your .env file.")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        response = httpx.post(
            OPENAI_CHAT_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        content = data["choices"][0]["message"].get("content") or ""
        return LLMResponse(
            text=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )