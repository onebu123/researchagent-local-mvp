from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_v1_readiness_and_export_keep_local_mvp_boundary(demo_project_dir: Path) -> None:
    client = TestClient(app)

    readiness_response = client.get("/api/projects/demo_project/trust/readiness-report")
    export_response = client.post("/api/projects/demo_project/export/zip")

    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert (demo_project_dir / "trust" / "v1_readiness_report.json").exists()
    assert readiness["readiness_level"] in {"local_mvp_ready", "needs_local_review"}
    assert "production_ready" not in readiness["readiness_level"]
    assert readiness["production_gaps"]
    assert any("No authentication" in gap for gap in readiness["production_gaps"])
    assert any("No real DOI" in gap for gap in readiness["production_gaps"])
    assert any("OCR" in gap for gap in readiness["production_gaps"])

    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert "local_mvp_caveats" in export_payload
    assert any("Local MVP export only" in item for item in export_payload["local_mvp_caveats"])
    assert not str(export_payload).lower().count("production_ready")
