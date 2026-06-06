from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_analysis_timeline_links_comparisons_to_real_run_history(demo_project_dir: Path) -> None:
    client = TestClient(app)
    compare_response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )
    assert compare_response.status_code == 200
    comparison_id = compare_response.json()["comparison_id"]

    timeline_response = client.get("/api/projects/demo_project/analysis/timeline")

    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert (demo_project_dir / "analysis" / "analysis_timeline.json").exists()
    assert "timeline" in timeline
    assert "unlinked_comparisons" in timeline
    all_linked = [
        comparison["comparison_id"]
        for entry in timeline["timeline"]
        for comparison in entry.get("comparisons", [])
    ]
    all_unlinked = [comparison["comparison_id"] for comparison in timeline["unlinked_comparisons"]]
    assert comparison_id in all_linked or comparison_id in all_unlinked
    assert all(not str(entry.get("run_id", "")).startswith("fake_") for entry in timeline["timeline"])
