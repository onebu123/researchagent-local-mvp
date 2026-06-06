from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from scripts.create_failure_fixture import create_failure_fixture


def test_v1_readiness_report_marks_local_mvp_boundaries(demo_project_dir: Path) -> None:
    client = TestClient(app)
    create_failure_fixture("demo_project")
    evidence_review = client.post(
        "/api/projects/demo_project/evidence/claims/claim_003/review",
        json={"human_status": "supported", "reason": "pytest readiness evidence review"},
    )
    assert evidence_review.status_code == 200
    text_preview = client.get("/api/projects/demo_project/literature/pdf-page-text-preview")
    assert text_preview.status_code == 200

    response = client.get("/api/projects/demo_project/trust/readiness-report")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "trust" / "v1_readiness_report.json").exists()
    assert payload["readiness_level"] in {"local_mvp_ready", "needs_local_review"}
    assert payload["local_mvp_checks"]["evidence_claim_review_workflow"] is True
    assert payload["local_mvp_checks"]["trust_summary"] is True
    assert payload["production_gaps"]
    assert any("No authentication" in item for item in payload["production_gaps"])
    assert "production_ready" not in payload["readiness_level"]
