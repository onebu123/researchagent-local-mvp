from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _issue_with_safe_diff(project_dir: Path) -> dict:
    report = _read_json(project_dir / "reviews" / "review_report.json")
    draft = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    for issue in report["sentence_issues"]:
        diff = issue.get("revision_diff")
        if isinstance(diff, dict) and diff.get("before") in draft and diff.get("after"):
            return issue
    raise AssertionError("demo review_report.json must include a draft-backed revision_diff")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision_diff(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.9 revision review"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch.json()['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.9 revision review confirm"},
    )
    assert confirm.status_code == 200
    version = confirm.json()["version"]
    response = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/generate",
        json={"base_file": "manuscript/draft.md", "target_file": version["file"]},
    )
    assert response.status_code == 200
    return response.json()


def test_revision_diff_review_records_human_status_without_modifying_manuscript(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    before_hash = _sha256(draft_path)
    diff = _revision_diff(client, demo_project_dir)
    change = diff["changes"][0]

    response = client.post(
        "/api/projects/demo_project/manuscript/"
        f"revision-diffs/{diff['revision_diff_id']}/changes/{change['change_id']}/review",
        json={"human_status": "needs_evidence", "reason": "claim needs manual evidence check"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["human_status"] == "needs_evidence"
    assert payload["revision_diff_id"] == diff["revision_diff_id"]
    assert payload["change_id"] == change["change_id"]
    assert payload["summary"]["summary"]["reviewed"] >= 1
    assert (demo_project_dir / "manuscript" / "revision_diffs" / "revision_diff_reviews.jsonl").exists()
    assert (demo_project_dir / "manuscript" / "revision_diffs" / "revision_diff_review_summary.json").exists()
    assert _sha256(draft_path) == before_hash

    list_response = client.get("/api/projects/demo_project/manuscript/revision-diffs/reviews")
    assert list_response.status_code == 200
    assert any(review["review_id"] == payload["review_id"] for review in list_response.json()["reviews"])


def test_revision_diff_review_failure_boundaries(demo_project_dir: Path) -> None:
    client = TestClient(app)

    invalid_status = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/"
        "revision_diff_999/changes/change_001/review",
        json={"human_status": "auto_accept", "reason": "invalid"},
    )
    assert invalid_status.status_code == 422

    missing_diff = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/"
        "revision_diff_999/changes/change_001/review",
        json={"human_status": "accepted", "reason": "missing diff"},
    )
    assert missing_diff.status_code == 404
