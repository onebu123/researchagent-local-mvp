from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.literature_rag import ask_literature_rag, build_literature_rag, read_rag_chunks
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
