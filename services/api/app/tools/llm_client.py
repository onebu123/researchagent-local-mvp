from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.config import settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    mode: str
    provider: str
    model: str
    prompt_version: str
    status: str
    parsed_json: dict[str, Any] | list[Any] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    attempts: int = 0


class LLMClient:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = (mode or settings.llm_mode or "mock").strip().lower()

    @property
    def live_enabled(self) -> bool:
        return self.mode == "live" and bool(settings.llm_api_key.strip())

    def status(self) -> dict[str, Any]:
        parsed = urlparse(settings.llm_base_url)
        return {
            "mode": self.mode if self.mode in {"mock", "live"} else "mock",
            "effective_mode": "live" if self.live_enabled else "mock",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "base_url_host": parsed.netloc or parsed.path,
            "api_key_configured": bool(settings.llm_api_key.strip()),
            "timeout_seconds": settings.llm_timeout_seconds,
            "max_retries": settings.llm_max_retries,
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        fallback: str,
        prompt_version: str = "unversioned",
    ) -> LLMResponse:
        if not self.live_enabled:
            return LLMResponse(
                content=fallback,
                mode="mock",
                provider=settings.llm_provider,
                model=settings.llm_model,
                prompt_version=prompt_version,
                status="fallback",
            )

        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
        }
        attempts = settings.llm_max_retries + 1
        last_error: str | None = None
        for attempt in range(1, attempts + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    data=data,
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(
                    request,
                    timeout=settings.llm_timeout_seconds,
                ) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                content = response_data["choices"][0]["message"]["content"]
                usage = response_data.get("usage") if isinstance(response_data, dict) else None
                return LLMResponse(
                    content=str(content),
                    mode="live",
                    provider=settings.llm_provider,
                    model=settings.llm_model,
                    prompt_version=prompt_version,
                    status="success",
                    usage=usage if isinstance(usage, dict) else {},
                    attempts=attempt,
                )
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
                TimeoutError,
                OSError,
            ) as exc:
                last_error = exc.__class__.__name__
                if attempt < attempts:
                    time.sleep(min(0.25 * attempt, 1.0))

        return LLMResponse(
            content=fallback,
            mode="mock-fallback",
            provider=settings.llm_provider,
            model=settings.llm_model,
            prompt_version=prompt_version,
            status="fallback",
            error=last_error,
            attempts=attempts,
        )

    def chat_json(
        self,
        messages: list[dict[str, str]],
        fallback: dict[str, Any],
        prompt_version: str,
    ) -> LLMResponse:
        fallback_content = json.dumps(fallback, ensure_ascii=False)
        response = self.chat(messages, fallback_content, prompt_version=prompt_version)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = fallback
            response = LLMResponse(
                content=fallback_content,
                mode=response.mode if response.mode != "live" else "mock-fallback",
                provider=response.provider,
                model=response.model,
                prompt_version=response.prompt_version,
                status="fallback",
                parsed_json=parsed,
                usage=response.usage,
                error="json_parse_failed",
                attempts=response.attempts,
            )
            return response

        return LLMResponse(
            content=response.content,
            mode=response.mode,
            provider=response.provider,
            model=response.model,
            prompt_version=response.prompt_version,
            status=response.status,
            parsed_json=parsed if isinstance(parsed, (dict, list)) else fallback,
            usage=response.usage,
            error=response.error,
            attempts=response.attempts,
        )


llm_client = LLMClient()
