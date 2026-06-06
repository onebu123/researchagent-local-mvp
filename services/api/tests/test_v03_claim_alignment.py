from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.workflow_service import workflow_service
from main import app


def test_claim_alignment_exists_and_matches_claim(demo_project_dir: Path) -> None:
    alignment = json.loads(
        (demo_project_dir / "provenance" / "claim_alignment.json").read_text(encoding="utf-8")
    )

    assert alignment["summary"]["total_sentences_checked"] >= 1
    assert any(
        item.get("section") == "Results" for item in alignment.get("aligned_claims", [])
    )
    assert any(
        item.get("matched_claim_id") for item in alignment.get("aligned_claims", [])
    )


def test_claim_alignment_api_returns_object(demo_project_dir: Path) -> None:
    response = TestClient(app).get("/api/projects/demo_project/claim-alignment")

    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["aligned_claims"]


def test_claim_alignment_flags_unmatched_results_sentence(demo_project_dir: Path) -> None:
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original = draft_path.read_text(encoding="utf-8")
    inserted = "The storage response exceeded the expected range without a supporting claim."
    try:
        draft_path.write_text(
            original.replace("# Discussion", f"{inserted}\n\n# Discussion", 1),
            encoding="utf-8",
        )
        response = workflow_service.run_step("demo_project", "claim_alignment")
        assert response.workflow_status == "completed"
        alignment = json.loads(
            (demo_project_dir / "provenance" / "claim_alignment.json").read_text(encoding="utf-8")
        )
        assert any(
            inserted in item.get("sentence", "")
            and item.get("match_status") == "needs_claim_alignment"
            for item in alignment["aligned_claims"]
        )
    finally:
        draft_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "claim_alignment")
        workflow_service.run_step("demo_project", "reviewer")
