from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.workflow_service import workflow_service
from main import app


def test_literature_api_get_and_patch_metadata(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    original_draft = (demo_project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    try:
        get_response = client.get("/api/projects/demo_project/literature")
        assert get_response.status_code == 200
        records = get_response.json()
        assert isinstance(records, list)
        assert records

        literature_id = records[0]["literature_id"]
        patch_response = client.patch(
            f"/api/projects/demo_project/literature/{literature_id}",
            json={
                "title": "Manual verified demo record",
                "authors": ["Human Reviewer"],
                "year": 2024,
                "doi": "10.1234/demo-record",
                "journal": "Manual Metadata Journal",
                "metadata_status": "verified",
                "human_verified": True,
            },
        )
        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["metadata_status"] == "verified"
        assert updated["human_verified"] is True

        saved_index = json.loads(index_path.read_text(encoding="utf-8"))
        saved_record = next(item for item in saved_index if item["literature_id"] == literature_id)
        assert saved_record["doi"] == "10.1234/demo-record"

        workflow_service.run_step("demo_project", "manuscript")
        draft = (demo_project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
        verified_section = draft.split("## Verified references", 1)[1]
        assert "10.1234/demo-record" in verified_section
    finally:
        index_path.write_text(original_index, encoding="utf-8")
        (demo_project_dir / "manuscript" / "draft.md").write_text(original_draft, encoding="utf-8")
        workflow_service.run_step("demo_project", "manuscript")
        workflow_service.run_step("demo_project", "claim_alignment")
        workflow_service.run_step("demo_project", "reviewer")


def test_literature_api_rejects_invalid_doi(demo_project_dir: Path) -> None:
    client = TestClient(app)
    records = client.get("/api/projects/demo_project/literature").json()
    literature_id = records[0]["literature_id"]

    response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={"doi": "invalid-doi"},
    )

    assert response.status_code == 422
