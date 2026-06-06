from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _issue_with_safe_diff(project_dir: Path) -> dict:
    report = _read_json(project_dir / "reviews" / "review_report.json")
    draft = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    for issue in report["sentence_issues"]:
        diff = issue.get("revision_diff")
        if isinstance(diff, dict) and diff.get("before") in draft and diff.get("after"):
            return issue
    raise AssertionError("demo review_report.json must include a safe draft-backed revision_diff")


def test_accepted_revision_decision_generates_patch_without_modifying_draft(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    issue = _issue_with_safe_diff(demo_project_dir)
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original_hash = _sha256_text(draft_path)

    rejected_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "rejected", "reason": "pytest v0.5 rejected control"},
    )
    assert rejected_response.status_code == 200
    rejected_decision = rejected_response.json()
    accepted_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.5 accepted patch source"},
    )
    assert accepted_response.status_code == 200
    accepted_decision = accepted_response.json()

    patch_response = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})

    assert patch_response.status_code == 200
    patch = patch_response.json()
    assert patch["status"] == "proposed"
    assert patch["source"] == "accepted_revision_decision"
    assert patch["source_manuscript"] == "manuscript/draft.md"
    assert patch["items"]
    decision_ids = {item["decision_id"] for item in patch["items"]}
    assert accepted_decision["decision_id"] in decision_ids
    assert rejected_decision["decision_id"] not in decision_ids
    for field in ["issue_id", "decision_id", "before", "after", "related_claim_id"]:
        assert field in patch["items"][0]
    assert _sha256_text(draft_path) == original_hash

    patch_id = patch["patch_id"]
    assert (demo_project_dir / "manuscript" / "patches" / f"{patch_id}.json").exists()
    assert (demo_project_dir / "manuscript" / "patches" / f"{patch_id}.preview.md").exists()

    list_response = client.get("/api/projects/demo_project/manuscript/patches")
    get_response = client.get(f"/api/projects/demo_project/manuscript/patches/{patch_id}")
    preview_response = client.get(f"/api/projects/demo_project/manuscript/patches/{patch_id}/preview")

    assert list_response.status_code == 200
    assert any(item["patch_id"] == patch_id for item in list_response.json())
    assert get_response.status_code == 200
    assert get_response.json()["patch_id"] == patch_id
    assert preview_response.status_code == 200
    assert "Manuscript Patch Preview" in preview_response.json()["content"]


def test_patch_missing_file_returns_404(demo_project_dir: Path) -> None:
    client = TestClient(app)

    response = client.get("/api/projects/demo_project/manuscript/patches/patch_missing")

    assert response.status_code == 404
