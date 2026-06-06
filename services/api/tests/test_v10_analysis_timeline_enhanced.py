from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from scripts.create_failure_fixture import create_failure_fixture


def test_enhanced_analysis_timeline_reports_change_and_failure_diagnostics(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    create_failure_fixture("demo_project")
    comparison_response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )
    assert comparison_response.status_code == 200

    response = client.get("/api/projects/demo_project/analysis/timeline/enhanced")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "analysis" / "analysis_timeline.json").exists()
    assert "change_summary" in payload
    assert payload["change_summary"]["comparisons_total"] >= 1
    assert payload["change_summary"]["failed_runs"] >= 1
    assert payload["failed_run_diagnostics"]
    assert any(item["is_fixture"] is True for item in payload["failed_run_diagnostics"])
    assert all(not str(entry.get("run_id", "")).startswith("fake_") for entry in payload["timeline"])
