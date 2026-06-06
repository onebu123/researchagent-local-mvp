from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_metadata_revert_execution_preview_does_not_modify_index(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature_id = json.loads(original_index)[0]["literature_id"]

    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "v0.10 metadata revert preview marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": None,
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert patch_response.status_code == 200
    history_response = client.get(f"/api/projects/demo_project/literature/{literature_id}/history")
    assert history_response.status_code == 200
    history_id = history_response.json()[-1]["history_id"]
    before_preview = index_path.read_text(encoding="utf-8")

    preview_response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata/revert-preview",
        json={"field": "title", "source_history_id": history_id},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["applied"] is False
    assert preview["literature_index_modified"] is False
    assert preview["would_change"] is True
    assert preview["safe_to_apply"] is True
    assert (demo_project_dir / preview["relative_path"]).exists()
    assert index_path.read_text(encoding="utf-8") == before_preview

    missing_history = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata/revert-preview",
        json={"field": "title", "source_history_id": "lit_hist_9999"},
    )
    assert missing_history.status_code == 404

    index_path.write_text(original_index, encoding="utf-8")
