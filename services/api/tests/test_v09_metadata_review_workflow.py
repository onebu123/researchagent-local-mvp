from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _metadata_change(client: TestClient, project_dir: Path) -> tuple[str, dict]:
    index_path = project_dir / "literature" / "literature_index.json"
    literature_id = json.loads(index_path.read_text(encoding="utf-8"))[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "v0.9 metadata review marker",
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
    changes = [
        change
        for record in diff_response.json()["records"]
        if record["literature_id"] == literature_id
        for change in record["changes"]
        if change["field"] == "title"
    ]
    assert changes
    return literature_id, changes[-1]


def test_metadata_review_action_records_decision_without_modifying_index(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature_id, change = _metadata_change(client, demo_project_dir)
    before_action = index_path.read_text(encoding="utf-8")

    response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata-review",
        json={
            "field": "title",
            "action": "needs_verification",
            "source_history_id": change["source_history_id"],
            "reason": "title still requires human verification",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "needs_verification"
    assert payload["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before_action
    assert (demo_project_dir / "literature" / "metadata_review_actions.jsonl").exists()
    assert (demo_project_dir / "literature" / "metadata_review_summary.json").exists()

    actions_response = client.get("/api/projects/demo_project/literature/metadata-review-actions")
    assert actions_response.status_code == 200
    assert any(action["review_action_id"] == payload["review_action_id"] for action in actions_response.json()["actions"])
    index_path.write_text(original_index, encoding="utf-8")


def test_metadata_review_failure_boundaries(demo_project_dir: Path) -> None:
    client = TestClient(app)

    invalid_action = client.post(
        "/api/projects/demo_project/literature/lit_001/metadata-review",
        json={
            "field": "title",
            "action": "auto_verify",
            "source_history_id": "lit_hist_001",
            "reason": "invalid",
        },
    )
    assert invalid_action.status_code == 422

    missing_literature = client.post(
        "/api/projects/demo_project/literature/lit_missing/metadata-review",
        json={
            "field": "title",
            "action": "accept_change",
            "source_history_id": "lit_hist_001",
            "reason": "missing",
        },
    )
    assert missing_literature.status_code in {400, 404}
