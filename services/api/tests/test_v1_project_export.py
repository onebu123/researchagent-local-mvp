from __future__ import annotations

import re
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_project_zip_export_contains_local_mvp_artifacts(demo_project_dir: Path) -> None:
    client = TestClient(app)

    assert client.get("/api/projects/demo_project/trust/summary").status_code == 200
    assert client.get("/api/projects/demo_project/trust/readiness-report").status_code == 200
    assert client.post("/api/projects/demo_project/audit/export").status_code == 200

    response = client.post("/api/projects/demo_project/export/zip")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["relative_path"].startswith("exports/")
    assert payload["relative_path"].endswith(".zip")
    assert payload["included_file_count"] >= 10
    assert payload["category_counts"]["manuscript"] >= 1
    assert payload["category_counts"]["provenance"] >= 1
    assert payload["category_counts"]["audit"] >= 1

    zip_path = demo_project_dir / payload["relative_path"]
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "README_EXPORT.md" in names
    assert "manuscript/draft.md" in names
    assert "provenance/evidence.json" in names
    assert "reviews/review_report.json" in names
    assert "trust/trust_summary.json" in names
    assert "trust/v1_readiness_report.json" in names
    assert "analysis/result_summary.json" in names
    assert "figures/figure_provenance.json" in names
    assert "literature/literature_index.json" in names
    assert "literature/pdf_quality_report.json" in names
    assert "runs/run_history.json" in names
    assert any(name.startswith("audit/exports/") for name in names)
    assert all(not name.startswith("/") and not re.match(r"^[A-Za-z]:", name) for name in names)
    assert all(".." not in Path(name).parts for name in names)

    latest = client.get("/api/projects/demo_project/export/zip")
    assert latest.status_code == 200
    assert latest.json()["relative_path"] == payload["relative_path"]


def test_project_zip_export_rejects_missing_project() -> None:
    client = TestClient(app)

    get_response = client.get("/api/projects/missing_project/export/zip")
    post_response = client.post("/api/projects/missing_project/export/zip")

    assert get_response.status_code == 404
    assert post_response.status_code == 404
