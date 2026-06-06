from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_filtered_audit_export_writes_json_and_markdown_without_sensitive_paths(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/projects/demo_project/audit/filtered-export",
        json={"risk_level": "low"},
    )

    assert response.status_code == 200
    export = response.json()
    assert export["export_id"].startswith("audit_filtered_export_")
    export_path = demo_project_dir / "audit" / "filtered_exports" / f"{export['export_id']}.json"
    assert export_path.exists()
    assert (demo_project_dir / export["report_file"]).exists()
    serialized = json.dumps(export, ensure_ascii=False)
    assert "sk_live_" not in serialized
    assert "D:\\" not in serialized
    assert ":/" not in serialized

    list_response = client.get("/api/projects/demo_project/audit/filtered-exports")
    assert list_response.status_code == 200
    assert any(item["export_id"] == export["export_id"] for item in list_response.json())

    get_response = client.get(f"/api/projects/demo_project/audit/filtered-exports/{export['export_id']}")
    report_response = client.get(
        f"/api/projects/demo_project/audit/filtered-exports/{export['export_id']}/report"
    )
    assert get_response.status_code == 200
    assert report_response.status_code == 200
    assert "# Filtered Audit Report" in report_response.json()["content"]


def test_filtered_audit_export_failure_boundaries() -> None:
    client = TestClient(app)

    invalid_filter = client.post(
        "/api/projects/demo_project/audit/filtered-export",
        json={"risk_level": "critical"},
    )
    assert invalid_filter.status_code == 422

    path_like_entity = client.post(
        "/api/projects/demo_project/audit/filtered-export",
        json={"entity_id": "../secret"},
    )
    assert path_like_entity.status_code == 422

    missing_export = client.get(
        "/api/projects/demo_project/audit/filtered-exports/audit_filtered_export_999/report"
    )
    assert missing_export.status_code == 404
