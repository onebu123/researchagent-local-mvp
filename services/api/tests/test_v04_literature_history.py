from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_literature_patch_writes_metadata_history(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature_index = json.loads(original_index)
    literature_id = literature_index[0]["literature_id"]

    try:
        response = client.patch(
            f"/api/projects/demo_project/literature/{literature_id}",
            json={
                "title": "v0.4 metadata history marker",
                "authors": [],
                "year": None,
                "doi": None,
                "journal": None,
                "metadata_status": "placeholder",
                "human_verified": False,
            },
        )
        assert response.status_code == 200
        history_path = demo_project_dir / "literature" / "metadata_history.jsonl"
        assert history_path.exists()
        records = [
            json.loads(line)
            for line in history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert any(
            record["literature_id"] == literature_id and "title" in record["changed_fields"]
            for record in records
        )
    finally:
        index_path.write_text(original_index, encoding="utf-8")


def test_literature_history_apis_return_records(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index = json.loads((demo_project_dir / "literature" / "literature_index.json").read_text(encoding="utf-8"))
    literature_id = index[0]["literature_id"]

    all_response = client.get("/api/projects/demo_project/literature/history")
    assert all_response.status_code == 200
    assert isinstance(all_response.json(), list)

    one_response = client.get(f"/api/projects/demo_project/literature/{literature_id}/history")
    assert one_response.status_code == 200
    assert isinstance(one_response.json(), list)


def test_literature_history_rejects_unknown_literature_id() -> None:
    client = TestClient(app)
    response = client.get("/api/projects/demo_project/literature/lit_unknown/history")
    assert response.status_code == 404
