from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.tools import literature_rag
from app.tools import llm_client as llm_client_module
from app.tools.literature_rag import ask_literature_rag, build_literature_rag, read_rag_chunks
from app.tools.llm_client import LLMResponse
from main import app


def test_literature_rag_build_and_ask_uses_real_chunks(demo_project_dir: Path) -> None:
    index = build_literature_rag(demo_project_dir, "demo_project")
    assert index["chunk_count"] > 0
    chunks = read_rag_chunks(demo_project_dir)
    assert chunks
    assert all(chunk["text"] for chunk in chunks)

    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "What does the demo literature mention about efficiency?",
    )
    assert answer["source_passages"]
    assert answer["llm_mode"] == "mock"
    assert answer["prompt_version"] == "literature_answer_v1"
    assert answer["retrieval_mode"] == "local_hybrid"
    assert answer["source_passage_count"] == len(answer["source_passages"])
    assert isinstance(answer["unsupported_notes"], list)
    assert answer["llm"]["prompt_version"] == "literature_answer_v1"
    assert (demo_project_dir / "literature" / "rag" / "rag_answers.jsonl").exists()
    assert (demo_project_dir / "llm" / "llm_calls.jsonl").exists()


def test_literature_rag_api_boundaries(demo_project_dir: Path) -> None:
    client = TestClient(app)
    build = client.post("/api/projects/demo_project/literature/rag/build")
    assert build.status_code == 200

    ask = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "efficiency stability", "top_k": 2},
    )
    assert ask.status_code == 200
    assert "source_passages" in ask.json()

    invalid = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "", "top_k": 2},
    )
    assert invalid.status_code == 422


def test_literature_rag_uses_configured_global_llm_client(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    class FakeLiveClient:
        def __init__(self) -> None:
            self.called = False

        def chat_json(self, messages, fallback, prompt_version):  # type: ignore[no-untyped-def]
            self.called = True
            return LLMResponse(
                content='{"answer":"fake live answer","unsupported_notes":[],"limitations":["fake client only"]}',
                mode="live",
                provider="fake",
                model="fake-model",
                prompt_version=prompt_version,
                status="success",
                parsed_json={
                    "answer": "fake live answer",
                    "unsupported_notes": [],
                    "limitations": ["fake client only"],
                },
            )

    fake_client = FakeLiveClient()
    monkeypatch.setattr(llm_client_module, "llm_client", fake_client)

    answer = literature_rag.ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "What does the demo literature mention about efficiency?",
    )

    assert fake_client.called is True
    assert answer["answer"] == "fake live answer"
    assert answer["llm_mode"] == "live"
    assert answer["llm"]["provider"] == "fake"
    assert answer["prompt_version"] == "literature_answer_v1"
    assert answer["retrieval_mode"] == "local_hybrid"
    assert answer["source_passage_count"] == len(answer["source_passages"])
    assert isinstance(answer["unsupported_notes"], list)
