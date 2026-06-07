from __future__ import annotations

from fastapi.testclient import TestClient

from app.tools.llm_client import LLMClient
from main import app


def test_llm_client_mock_chat_and_json_fallback() -> None:
    client = LLMClient(mode="mock")

    response = client.chat(
        [{"role": "user", "content": "hello"}],
        fallback="mock response",
        prompt_version="literature_answer_v1",
    )

    assert response.content == "mock response"
    assert response.mode == "mock"
    assert response.prompt_version == "literature_answer_v1"

    json_response = client.chat_json(
        [{"role": "user", "content": "return json"}],
        {"ok": True},
        prompt_version="literature_answer_v1",
    )
    assert json_response.parsed_json == {"ok": True}
    assert json_response.mode == "mock"


def test_llm_status_and_test_api_do_not_expose_key_name() -> None:
    client = TestClient(app)

    status = client.get("/api/system/llm/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["effective_mode"] in {"mock", "live"}
    assert "llm_api_key" not in status.text.lower()
    assert "authorization" not in status.text.lower()

    test_response = client.post(
        "/api/system/llm/test",
        json={"prompt": "Return a health check.", "prompt_version": "literature_answer_v1"},
    )
    assert test_response.status_code == 200
    test_payload = test_response.json()
    assert test_payload["prompt_version"] == "literature_answer_v1"
    assert test_payload["mode"] in {"mock", "live", "mock-fallback"}
