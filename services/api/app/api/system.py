from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import LLMTestRequest
from app.tools.llm_client import llm_client
from app.tools.prompt_registry import list_prompts, load_prompt

router = APIRouter()


@router.get("/system/llm/status")
def get_llm_status() -> dict[str, Any]:
    return llm_client.status()


@router.post("/system/llm/test")
def test_llm(payload: LLMTestRequest) -> dict[str, Any]:
    try:
        prompt = load_prompt(payload.prompt_version)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    fallback = {
        "ok": True,
        "message": "mock LLM test response",
        "prompt_version": prompt["prompt_version"],
    }
    messages = [
        {"role": "system", "content": prompt["content"]},
        {"role": "user", "content": payload.prompt},
    ]
    response = llm_client.chat_json(messages, fallback, prompt_version=prompt["prompt_version"])
    return {
        "ok": True,
        "content": response.parsed_json if response.parsed_json is not None else response.content,
        "raw_content": response.content if len(response.content) <= 1000 else response.content[:1000],
        "mode": response.mode,
        "provider": response.provider,
        "model": response.model,
        "prompt_version": response.prompt_version,
        "status": response.status,
        "usage": response.usage,
        "error": response.error,
    }


@router.get("/system/prompts")
def get_prompt_registry() -> dict[str, Any]:
    prompts = list_prompts(include_content=False)
    return {
        "prompts": prompts,
        "count": len(prompts),
        "required_prompt_versions": [
            "literature_answer_v1",
            "citation_support_v1",
            "metadata_extraction_v1",
            "bibtex_generation_v1",
        ],
    }
