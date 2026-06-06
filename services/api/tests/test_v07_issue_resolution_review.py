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
    raise AssertionError("demo review_report.json must include a safe draft-backed revision_diff")


def _create_confirmed_merge_for_issue(client: TestClient, project_dir: Path) -> tuple[dict, dict]:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.7 issue review decision"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    preview = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [patch.json()["patch_id"]]},
    )
    assert preview.status_code == 200
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/merges/{preview.json()['merge_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.7 issue review confirm"},
    )
    assert confirm.status_code == 200
    return issue, confirm.json()


def test_issue_resolution_human_review_records_status(demo_project_dir: Path) -> None:
    client = TestClient(app)
    issue, confirmed = _create_confirmed_merge_for_issue(client, demo_project_dir)
    version_id = confirmed["version"]["version_id"]

    response = client.post(
        f"/api/projects/demo_project/review/issue-resolution/{issue['issue_id']}/review",
        json={
            "version_id": version_id,
            "human_status": "resolved",
            "reason": "pytest v0.7 human review",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review"]["issue_id"] == issue["issue_id"]
    assert payload["review"]["version_id"] == version_id
    assert payload["review"]["human_status"] == "resolved"
    assert payload["review"]["auto_status"] in {"resolved", "partially_resolved", "unresolved", "unknown"}
    assert (demo_project_dir / "reviews" / "issue_resolution_reviews.jsonl").exists()
    assert payload["issue_resolution"]["summary"]["human_reviews"] >= 1

    get_response = client.get("/api/projects/demo_project/review/issue-resolution")
    assert get_response.status_code == 200
    matching = [
        item
        for item in get_response.json()["versions"]
        if item["version_id"] == version_id
    ]
    assert matching
    assert matching[0]["human_review_summary"]["reviewed"] >= 1
    assert any(review["issue_id"] == issue["issue_id"] for review in matching[0]["latest_human_reviews"])

    reviews_response = client.get("/api/projects/demo_project/review/issue-resolution/reviews")
    assert reviews_response.status_code == 200
    assert any(review["issue_id"] == issue["issue_id"] for review in reviews_response.json())
