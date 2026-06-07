from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.literature_rag import build_literature_rag
from app.tools.rag_quality import (
    generate_chunk_quality_report,
    generate_retrieval_eval_report,
    generate_retrieval_eval_set,
)
from main import app


def test_rag_quality_and_eval_reports_are_local_files(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")
    quality = generate_chunk_quality_report(demo_project_dir, "demo_project")
    eval_set = generate_retrieval_eval_set(demo_project_dir, "demo_project")
    eval_report = generate_retrieval_eval_report(demo_project_dir, "demo_project")

    assert quality["summary"]["total_chunks"] > 0
    assert quality["items"]
    assert quality["items"][0]["quality_score"] >= 0
    assert eval_set["cases"]
    assert eval_report["metrics"]["total_cases"] == len(eval_set["cases"])
    assert 0 <= eval_report["metrics"]["hit_at_3"] <= 1
    assert (demo_project_dir / "literature" / "rag" / "chunk_quality_report.json").exists()
    assert (demo_project_dir / "literature" / "rag" / "retrieval_eval_set.json").exists()
    assert (demo_project_dir / "literature" / "rag" / "retrieval_eval_report.json").exists()


def test_rag_quality_api_contracts(demo_project_dir: Path) -> None:
    client = TestClient(app)
    assert client.post("/api/projects/demo_project/literature/rag/build").status_code == 200

    ask = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "efficiency stability", "top_k": 2, "retrieval_mode": "local_hybrid"},
    )
    assert ask.status_code == 200
    assert ask.json()["retrieval"]["retrieval_mode"] == "local_hybrid"

    for method, path in [
        ("get", "/api/projects/demo_project/literature/rag/quality"),
        ("get", "/api/projects/demo_project/literature/rag/eval-set"),
        ("post", "/api/projects/demo_project/literature/rag/evaluate"),
        ("get", "/api/projects/demo_project/literature/rag/evaluation"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 200

    invalid = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "efficiency", "top_k": 2, "retrieval_mode": "external_vector"},
    )
    assert invalid.status_code == 422
