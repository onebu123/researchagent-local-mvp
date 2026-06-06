from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_metadata_diff_and_revert_suggestion_do_not_modify_index(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature_id = json.loads(original_index)[0]["literature_id"]

    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "v0.8 field diff marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": None,
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert patch_response.status_code == 200

    diff_response = client.get("/api/projects/demo_project/literature/metadata-diff")
    assert diff_response.status_code == 200
    report = diff_response.json()
    assert (demo_project_dir / "literature" / "metadata_diff_report.json").exists()
    changes = [
        change
        for record in report["records"]
        for change in record["changes"]
        if record["literature_id"] == literature_id
    ]
    assert changes
    assert all("field" in change and "old_value" in change and "new_value" in change for change in changes)
    title_change = next(change for change in changes if change["field"] == "title")

    before_revert_suggestion = index_path.read_text(encoding="utf-8")
    suggestion_response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata/revert-suggestion",
        json={"field": "title", "source_history_id": title_change["source_history_id"]},
    )
    assert suggestion_response.status_code == 200
    suggestion = suggestion_response.json()
    assert suggestion["applied"] is False
    assert suggestion["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before_revert_suggestion

    index_path.write_text(original_index, encoding="utf-8")


def test_metadata_batch_review_marks_placeholder_without_modifying_index(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    before = index_path.read_text(encoding="utf-8")

    response = client.post("/api/projects/demo_project/literature/metadata-review-batch")

    assert response.status_code == 200
    batch = response.json()
    assert (demo_project_dir / "literature" / "metadata_review_batch.json").exists()
    assert batch["literature_index_modified"] is False
    assert batch["summary"]["total_records"] == len(batch["records"])
    placeholders = [
        record for record in batch["records"] if record["metadata_status"] == "placeholder"
    ]
    assert placeholders
    assert all(record["recommended_action"] == "manual_review_required" for record in placeholders)
    assert index_path.read_text(encoding="utf-8") == before

