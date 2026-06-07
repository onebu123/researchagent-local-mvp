from __future__ import annotations

from pathlib import Path

from app.tools.llm_call_log import append_llm_call, read_llm_calls
from app.tools.llm_client import LLMResponse


def test_llm_call_log_stores_summaries_not_full_prompt(tmp_path: Path) -> None:
    response = LLMResponse(
        content="draft answer",
        mode="mock",
        provider="openai-compatible",
        model="gpt-4o-mini",
        prompt_version="literature_answer_v1",
        status="fallback",
    )

    record = append_llm_call(
        tmp_path,
        "demo_project",
        "pytest.llm",
        [{"role": "user", "content": "This is a sensitive full prompt body."}],
        response,
    )

    assert record["request_summary"]["message_count"] == 1
    assert "This is a sensitive full prompt body" not in (tmp_path / "llm" / "llm_calls.jsonl").read_text(
        encoding="utf-8"
    )
    assert read_llm_calls(tmp_path)[0]["call_id"] == "llm_call_0001"
