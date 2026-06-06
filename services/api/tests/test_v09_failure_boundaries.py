from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_v09_endpoints_reject_missing_project() -> None:
    client = TestClient(app)

    responses = [
        client.get("/api/projects/missing_project/manuscript/revision-diffs/reviews"),
        client.get("/api/projects/missing_project/literature/metadata-review-actions"),
        client.get("/api/projects/missing_project/literature/pdf-page-reviews"),
        client.get("/api/projects/missing_project/analysis/timeline"),
        client.get("/api/projects/missing_project/audit/filtered-exports"),
    ]

    assert all(response.status_code == 404 for response in responses)
