from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_global_trust_summary_reports_open_and_blocking_items(demo_project_dir: Path) -> None:
    client = TestClient(app)
    review_response = client.post(
        "/api/projects/demo_project/evidence/claims/claim_002/review",
        json={"human_status": "unsupported", "reason": "pytest blocking trust item"},
    )
    assert review_response.status_code == 200

    response = client.get("/api/projects/demo_project/trust/summary")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "trust" / "trust_summary.json").exists()
    assert payload["overall_status"] == "needs_review"
    assert payload["counts"]["claims_total"] >= 1
    assert payload["counts"]["claims_unsupported"] >= 1
    assert payload["blocking_issues"]
    assert any(item["item_type"] == "evidence_claim" for item in payload["blocking_issues"])
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "sk_live_" not in serialized
    assert "api_key" not in serialized.lower()
    assert ":\\" not in serialized and ":/" not in serialized
