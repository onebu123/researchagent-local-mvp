from __future__ import annotations

from pathlib import Path

from app.tools.llm_call_log import append_llm_call
from app.tools.llm_client import LLMResponse


def test_llm_call_log_redacts_secrets_and_absolute_paths(tmp_path: Path) -> None:
    response = LLMResponse(
        content="response with sk-live-secret and C:\\Users\\name\\file.txt",
        mode="mock",
        provider="openai-compatible",
        model="gpt-4o-mini",
        prompt_version="literature_answer_v1",
        status="fallback",
    )
    append_llm_call(
        tmp_path,
        "demo_project",
        "pytest.secret",
        [
            {
                "role": "user",
                "content": "api_key=sk-live-secret C:\\Users\\name\\private.txt full prompt",
            }
        ],
        response,
        metadata={"path": "C:\\Users\\name\\private.txt", "token": "sk-live-secret"},
    )

    raw_log = (tmp_path / "llm" / "llm_calls.jsonl").read_text(encoding="utf-8")
    raw_audit = (tmp_path / "audit" / "audit_log.jsonl").read_text(encoding="utf-8")
    combined = raw_log + raw_audit
    assert "sk-live-secret" not in combined
    assert "C:\\Users\\name" not in combined
    assert "api_key=" not in combined
    assert "api_key=sk-live-secret C:\\Users\\name\\private.txt full prompt" not in combined
