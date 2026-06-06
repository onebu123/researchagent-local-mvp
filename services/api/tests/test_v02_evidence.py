from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.schemas import ProjectCreate
from app.services.project_service import project_service
from main import app


def test_evidence_has_three_claims_and_checklist_ids(demo_project_dir: Path) -> None:
    evidence = json.loads(
        (demo_project_dir / "provenance" / "evidence.json").read_text(encoding="utf-8")
    )
    draft = (demo_project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    checklist = draft.split("Evidence Checklist", 1)[1]

    claim_ids = {claim["claim_id"] for claim in evidence}
    assert len(evidence) >= 3
    assert any(claim["evidence_type"] == "figure" for claim in evidence)
    assert all(claim["claim_id"] in checklist for claim in evidence)
    assert claim_ids >= {"claim_001", "claim_002", "claim_003"}


def test_v02_evidence_and_figure_api_return_lists(demo_project_dir: Path) -> None:
    client = TestClient(app)

    evidence_response = client.get("/api/projects/demo_project/evidence")
    figure_response = client.get("/api/projects/demo_project/figures/provenance")

    assert evidence_response.status_code == 200
    assert isinstance(evidence_response.json(), list)
    assert figure_response.status_code == 200
    assert isinstance(figure_response.json(), list)


def test_v02_evidence_api_returns_404_when_file_missing() -> None:
    project_id = f"missing_v02_{uuid.uuid4().hex[:8]}"
    project_service.create_project(
        ProjectCreate(name="Missing v0.2 Project"),
        project_id=project_id,
        overwrite=True,
    )
    response = TestClient(app).get(f"/api/projects/{project_id}/evidence")

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]
