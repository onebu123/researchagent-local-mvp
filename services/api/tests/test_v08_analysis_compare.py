from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_analysis_compare_generates_comparison_report(demo_project_dir: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["comparison_id"].startswith("analysis_compare_")
    assert (demo_project_dir / comparison["relative_path"]).exists()
    for field in [
        "parameters",
        "input_data_hash",
        "output_file_hashes",
        "runtime",
        "warnings",
        "limitations",
    ]:
        assert field in comparison["diffs"]

    list_response = client.get("/api/projects/demo_project/analysis/comparisons")
    get_response = client.get(
        f"/api/projects/demo_project/analysis/comparisons/{comparison['comparison_id']}"
    )
    assert list_response.status_code == 200
    assert any(item["comparison_id"] == comparison["comparison_id"] for item in list_response.json())
    assert get_response.status_code == 200
    assert get_response.json()["comparison_id"] == comparison["comparison_id"]

