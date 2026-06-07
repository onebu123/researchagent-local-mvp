from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.reference_verification import run_reference_verification
from main import app
from v12_helpers import base_literature_entry, write_v12_project


def test_reference_verification_generates_candidates_without_modifying_index(tmp_path: Path) -> None:
    index_path = write_v12_project(tmp_path, [base_literature_entry()])
    before = index_path.read_text(encoding="utf-8")

    payload = run_reference_verification(tmp_path, "tmp_project")

    assert payload["summary"]["total"] == 1
    assert payload["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before
    result = payload["results"][0]
    assert result["provider"] == "mock_fixture"
    assert result["status"] == "needs_human_review"
    assert result["candidate"]["doi"] is None
    assert result["candidate"]["title"] == "Adaptive Retrieval Improves Local Citation Grounding"


def test_reference_verification_api_contract_does_not_auto_apply(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    before = index_path.read_text(encoding="utf-8")

    response = client.post(
        "/api/projects/demo_project/literature/reference-verification/run",
        json={"provider": "mock_fixture"},
    )

    assert response.status_code == 200
    assert response.json()["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before

    results = client.get("/api/projects/demo_project/literature/reference-verification/results")
    summary = client.get("/api/projects/demo_project/literature/reference-verification/summary")
    assert results.status_code == 200
    assert summary.status_code == 200
    assert isinstance(results.json(), list)
    assert summary.json()["summary"]["total"] >= 1

    # 确认响应中没有凭空写入 DOI。
    current = json.loads(index_path.read_text(encoding="utf-8"))
    assert all(entry.get("doi") is None for entry in current if entry.get("metadata_status") == "placeholder")
