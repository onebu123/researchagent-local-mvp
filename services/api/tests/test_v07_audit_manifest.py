from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _contains_forbidden_value(value) -> bool:
    if isinstance(value, dict):
        return any(_contains_forbidden_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_value(item) for item in value)
    if isinstance(value, str):
        return (
            "sk_live_" in value
            or "api_key" in value.lower()
            or bool(re.search(r"[A-Za-z]:[\\/]", value))
        )
    return False


def test_audit_export_generates_file_manifest(demo_project_dir: Path) -> None:
    client = TestClient(app)

    response = client.post("/api/projects/demo_project/audit/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest_file"].startswith("audit/exports/audit_file_manifest_")
    manifest_path = demo_project_dir / payload["manifest_file"]
    assert manifest_path.exists()

    manifest_response = client.get(
        f"/api/projects/demo_project/audit/exports/{payload['export_id']}/manifest"
    )
    report_response = client.get(
        f"/api/projects/demo_project/audit/exports/{payload['export_id']}/report"
    )

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["export_id"] == payload["export_id"]
    assert manifest["file_count"] == len(manifest["files"])
    assert manifest["files"]
    assert all("relative_path" in item and "sha256" in item for item in manifest["files"])
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])
    assert not _contains_forbidden_value(manifest)
    assert any(item["relative_path"] == "manuscript/draft.md" for item in manifest["files"])

    assert report_response.status_code == 200
    report = report_response.json()["content"]
    assert "File Manifest Summary" in report
    assert "Files hashed" in report
