from __future__ import annotations

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


def _revision_diff(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.10 closure"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch.json()['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.10 closure confirm"},
    )
    assert confirm.status_code == 200
    version = confirm.json()["version"]
    response = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/generate",
        json={"base_file": "manuscript/draft.md", "target_file": version["file"]},
    )
    assert response.status_code == 200
    return response.json()


def test_reviewer_closure_summary_links_issues_to_accepted_revision_reviews(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    diff = _revision_diff(client, demo_project_dir)
    change = diff["changes"][0]
    review = client.post(
        "/api/projects/demo_project/manuscript/"
        f"revision-diffs/{diff['revision_diff_id']}/changes/{change['change_id']}/review",
        json={"human_status": "accepted", "reason": "pytest closure accepts revision change"},
    )
    assert review.status_code == 200

    response = client.get("/api/projects/demo_project/review/closure-summary")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "reviews" / "reviewer_closure_summary.json").exists()
    assert payload["summary"]["total_sentence_issues"] >= 1
    assert payload["summary"]["closed"] >= 1
    closed = [issue for issue in payload["issues"] if issue["closure_status"] == "closed"]
    assert closed
    assert closed[0]["latest_revision_review"]["human_status"] == "accepted"
    assert "workflow closure only" in closed[0]["reason"]
