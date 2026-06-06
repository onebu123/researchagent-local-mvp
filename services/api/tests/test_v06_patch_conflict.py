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


def _create_patch(client: TestClient, project_dir: Path, reason: str) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": reason},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    assert patch.json()["items"]
    return patch.json()


def test_patch_conflict_detects_same_before_and_same_sentence(demo_project_dir: Path) -> None:
    client = TestClient(app)
    first = _create_patch(client, demo_project_dir, "pytest v0.6 conflict first")
    second = _create_patch(client, demo_project_dir, "pytest v0.6 conflict second")

    response = client.post(
        "/api/projects/demo_project/manuscript/patches/conflicts/check",
        json={"patch_ids": [first["patch_id"], second["patch_id"]]},
    )

    assert response.status_code == 200
    report = response.json()
    conflict_types = {item["conflict_type"] for item in report["conflicts"]}
    assert "same_before_text" in conflict_types
    assert "same_sentence" in conflict_types
    assert report["summary"]["major_conflicts"] >= 1
    assert (
        demo_project_dir
        / "manuscript"
        / "patches"
        / f"{report['conflict_report_id'].replace('conflict_', 'conflict_report_')}.json"
    ).exists()


def test_patch_conflict_reports_unsafe_item(demo_project_dir: Path) -> None:
    client = TestClient(app)
    patch = _create_patch(client, demo_project_dir, "pytest v0.6 unsafe conflict")
    item = patch["items"][0]
    edit = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/items/{item['patch_item_id']}",
        json={"after": f"{item['after']} This proved a causal effect.", "reason": "make unsafe"},
    )
    assert edit.status_code == 200

    response = client.post(
        "/api/projects/demo_project/manuscript/patches/conflicts/check",
        json={"patch_ids": [patch["patch_id"]]},
    )

    assert response.status_code == 200
    assert "unsafe_item" in {item["conflict_type"] for item in response.json()["conflicts"]}

