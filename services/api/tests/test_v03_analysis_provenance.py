from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_analysis_provenance_file_exists_and_has_required_fields(demo_project_dir: Path) -> None:
    provenance = json.loads(
        (demo_project_dir / "analysis" / "analysis_provenance.json").read_text(encoding="utf-8")
    )

    assert provenance["input_data_hash"]
    assert provenance["analysis_function"] == "app.tools.csv_profile.profile_csv"
    assert provenance["generated_files"]
    assert provenance["runtime"]["python_version"]
    assert provenance["runtime"]["pandas_version"]
    assert provenance["runtime"]["numpy_version"]
    assert provenance["is_demo_data"] is True


def test_evidence_analysis_claim_binds_analysis_provenance(demo_project_dir: Path) -> None:
    evidence = json.loads(
        (demo_project_dir / "provenance" / "evidence.json").read_text(encoding="utf-8")
    )
    analysis_claims = [
        claim for claim in evidence if claim.get("evidence_type") in {"analysis", "analysis_summary"}
    ]

    assert analysis_claims
    assert all(
        claim.get("analysis_provenance_file") == "analysis/analysis_provenance.json"
        for claim in analysis_claims
    )


def test_v03_new_read_apis_return_data(demo_project_dir: Path) -> None:
    client = TestClient(app)

    endpoints = [
        "/api/projects/demo_project/analysis/provenance",
        "/api/projects/demo_project/claim-alignment",
        "/api/projects/demo_project/literature",
        "/api/projects/demo_project/review/sentence-issues",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200, endpoint
        assert response.json() is not None
