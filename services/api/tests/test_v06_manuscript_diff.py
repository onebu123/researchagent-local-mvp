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


def _confirmed_version(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.6 diff source"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    confirm = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch.json()['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.6 diff confirm"},
    )
    assert confirm.status_code == 200
    return confirm.json()["version"]


def test_manuscript_diff_generates_json_and_markdown(demo_project_dir: Path) -> None:
    client = TestClient(app)
    version = _confirmed_version(client, demo_project_dir)

    response = client.post(
        "/api/projects/demo_project/manuscript/diffs/generate",
        json={"base_file": "manuscript/draft.md", "version_id": version["version_id"]},
    )

    assert response.status_code == 200
    diff = response.json()
    assert diff["summary"]["changed_hunks"] >= 1
    assert diff["hunks"]
    assert diff["hunks"][0]["added"]
    assert diff["hunks"][0]["removed"]
    assert "related_issue_ids" in diff["hunks"][0]
    assert "related_claim_ids" in diff["hunks"][0]
    assert (demo_project_dir / "manuscript" / "diffs" / f"{diff['diff_id']}.json").exists()
    assert (demo_project_dir / "manuscript" / "diffs" / f"{diff['diff_id']}.md").exists()

    list_response = client.get("/api/projects/demo_project/manuscript/diffs")
    get_response = client.get(f"/api/projects/demo_project/manuscript/diffs/{diff['diff_id']}")
    preview_response = client.get(
        f"/api/projects/demo_project/manuscript/diffs/{diff['diff_id']}/preview"
    )
    assert list_response.status_code == 200
    assert any(item["diff_id"] == diff["diff_id"] for item in list_response.json())
    assert get_response.status_code == 200
    assert get_response.json()["diff_id"] == diff["diff_id"]
    assert preview_response.status_code == 200
    assert "Manuscript Diff" in preview_response.json()["content"]

