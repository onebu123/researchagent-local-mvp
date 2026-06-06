from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    mode: str


class LLMClient:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode or settings.llm_mode

    def chat(self, messages: list[dict[str, str]], fallback: str) -> LLMResponse:
        if self.mode == "mock" or not settings.llm_api_key:
            return LLMResponse(content=fallback, mode="mock")
        try:
            payload = json.dumps(
                {
                    "model": settings.llm_model,
                    "messages": messages,
                    "temperature": 0.2,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return LLMResponse(content=content, mode="openai-compatible")
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError):
            return LLMResponse(content=fallback, mode="mock-fallback")


llm_client = LLMClient()
