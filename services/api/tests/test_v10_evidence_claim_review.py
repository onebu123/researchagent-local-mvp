from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_evidence_claim_review_records_status_without_modifying_evidence(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    evidence_path = demo_project_dir / "provenance" / "evidence.json"
    before_hash = _sha256(evidence_path)

    response = client.post(
        "/api/projects/demo_project/evidence/claims/claim_001/review",
        json={
            "human_status": "supported",
            "reason": "pytest v0.10 evidence claim review",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["claim_id"] == "claim_001"
    assert payload["human_status"] == "supported"
    assert payload["evidence_modified"] is False
    assert payload["summary"]["summary"]["reviewed"] >= 1
    assert (demo_project_dir / "provenance" / "evidence_claim_reviews.jsonl").exists()
    assert (demo_project_dir / "provenance" / "evidence_claim_review_summary.json").exists()
    assert _sha256(evidence_path) == before_hash

    list_response = client.get("/api/projects/demo_project/evidence/claim-reviews")
    assert list_response.status_code == 200
    assert any(review["review_id"] == payload["review_id"] for review in list_response.json()["reviews"])


def test_evidence_claim_review_failure_boundaries(demo_project_dir: Path) -> None:
    client = TestClient(app)

    invalid_status = client.post(
        "/api/projects/demo_project/evidence/claims/claim_001/review",
        json={"human_status": "auto_supported", "reason": "invalid"},
    )
    assert invalid_status.status_code == 422

    missing_claim = client.post(
        "/api/projects/demo_project/evidence/claims/claim_999/review",
        json={"human_status": "supported", "reason": "missing claim"},
    )
    assert missing_claim.status_code == 404

    invalid_claim_id = client.post(
        "/api/projects/demo_project/evidence/claims/not_a_claim/review",
        json={"human_status": "supported", "reason": "bad id"},
    )
    assert invalid_claim_id.status_code == 400
