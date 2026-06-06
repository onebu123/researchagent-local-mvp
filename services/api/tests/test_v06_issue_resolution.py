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


def _create_patch(client: TestClient, project_dir: Path, reason: str) -> tuple[dict, dict]:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": reason},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    assert patch.json()["items"]
    return issue, patch.json()


def test_issue_resolution_marks_applied_issue_resolved(demo_project_dir: Path) -> None:
    client = TestClient(app)
    issue, patch = _create_patch(client, demo_project_dir, "pytest v0.6 issue resolved")
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.6 issue confirm"},
    )
    assert confirm.status_code == 200
    (demo_project_dir / "reviews" / "issue_resolution.json").unlink(missing_ok=True)

    response = client.get("/api/projects/demo_project/review/issue-resolution")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "reviews" / "issue_resolution.json").exists()
    matching_versions = [
        item
        for item in payload["versions"]
        if item["version_id"] == confirm.json()["version"]["version_id"]
    ]
    assert matching_versions
    assert issue["issue_id"] in matching_versions[0]["resolved_issue_ids"]


def test_issue_resolution_does_not_mark_skipped_issue_resolved(demo_project_dir: Path) -> None:
    client = TestClient(app)
    issue, patch = _create_patch(client, demo_project_dir, "pytest v0.6 issue skipped")
    item = patch["items"][0]
    edit = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/items/{item['patch_item_id']}",
        json={"after": f"{item['after']} This proved a causal effect.", "reason": "skip item"},
    )
    assert edit.status_code == 200
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.6 skipped confirm"},
    )
    assert confirm.status_code == 200
    (demo_project_dir / "reviews" / "issue_resolution.json").unlink(missing_ok=True)

    response = client.get("/api/projects/demo_project/review/issue-resolution")

    assert response.status_code == 200
    matching_versions = [
        item
        for item in response.json()["versions"]
        if item["version_id"] == confirm.json()["version"]["version_id"]
    ]
    assert matching_versions
    assert issue["issue_id"] not in matching_versions[0]["resolved_issue_ids"]
    assert issue["issue_id"] in (
        matching_versions[0]["partially_resolved_issue_ids"]
        + matching_versions[0]["unresolved_issue_ids"]
    )

