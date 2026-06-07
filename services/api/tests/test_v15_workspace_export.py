from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.workspace_export import build_workspace_export
from main import app


def test_workspace_export_generates_manifest_and_artifacts(demo_project_dir: Path) -> None:
    manifest = build_workspace_export(demo_project_dir, "demo_project")

    assert manifest["available"] is True
    assert manifest["relative_path"] == "exports/workspace/workspace_export_manifest.json"
    assert manifest["export_dir"] == "exports/workspace"
    assert manifest["safety"]["project_relative_paths_only"] is True
    assert manifest["safety"]["secret_scan_passed"] is True

    artifact_paths = {item["relative_path"] for item in manifest["artifacts"]}
    assert "exports/workspace/research_workspace_export.docx" in artifact_paths
    assert "exports/workspace/research_workspace_export.tex" in artifact_paths
    assert "exports/workspace/trust_report.md" in artifact_paths
    assert "exports/workspace/trust_report.json" in artifact_paths
    assert "exports/workspace/workspace_export_manifest.json" in artifact_paths

    for item in manifest["artifacts"]:
        assert item["relative_path"].startswith("exports/workspace/")
        assert not Path(item["relative_path"]).is_absolute()
        assert ".." not in Path(item["relative_path"]).parts
        assert (demo_project_dir / item["relative_path"]).exists()
        if item["artifact_type"] != "workspace_export_manifest":
            assert item["size_bytes"] > 0
            assert isinstance(item["sha256"], str)


def test_workspace_export_api_contracts(demo_project_dir: Path) -> None:
    client = TestClient(app)

    created = client.post("/api/projects/demo_project/export/workspace")
    assert created.status_code == 200
    payload = created.json()
    assert payload["available"] is True
    assert payload["relative_path"] == "exports/workspace/workspace_export_manifest.json"
    assert payload["artifacts"]
    assert payload["source_files"]

    latest = client.get("/api/projects/demo_project/export/workspace")
    assert latest.status_code == 200
    assert latest.json()["relative_path"] == payload["relative_path"]

    missing = client.get("/api/projects/missing_project/export/workspace")
    assert missing.status_code == 404


def test_workspace_export_records_audit_event(demo_project_dir: Path) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    audit_log = (demo_project_dir / "audit" / "audit_log.jsonl").read_text(encoding="utf-8")

    assert "generate_workspace_export" in audit_log
    assert "exports/workspace/workspace_export_manifest.json" in audit_log
