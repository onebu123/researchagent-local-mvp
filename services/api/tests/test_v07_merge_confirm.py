from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_confirm_merge_creates_version_diff_and_keeps_draft(demo_project_dir: Path) -> None:
    client = TestClient(app)
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    draft_hash = _sha256(draft_path)
    patch = _create_patch(client, demo_project_dir, "pytest v0.7 merge confirm")

    preview = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [patch["patch_id"]]},
    )
    assert preview.status_code == 200
    merge = preview.json()
    assert merge["can_apply"] is True

    response = client.post(
        f"/api/projects/demo_project/manuscript/patches/merges/{merge['merge_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest v0.7 merge confirm"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["merge"]["status"] == "confirmed"
    assert payload["version"] is not None
    assert payload["diff"] is not None
    assert payload["version"]["source_type"] == "merge"
    assert payload["version"]["source_merge_id"] == merge["merge_id"]
    assert patch["patch_id"] in payload["version"]["source_patch_ids"]
    assert payload["merge"]["generated_version_id"] == payload["version"]["version_id"]
    assert payload["merge"]["generated_diff_id"] == payload["diff"]["diff_id"]
    assert _sha256(draft_path) == draft_hash
    assert (
        demo_project_dir / "manuscript" / "versions" / f"{payload['version']['version_id']}.md"
    ).exists()
    assert (demo_project_dir / payload["diff"]["relative_path"]).exists()


def test_reject_merge_does_not_create_version(demo_project_dir: Path) -> None:
    client = TestClient(app)
    patch = _create_patch(client, demo_project_dir, "pytest v0.7 merge reject")
    preview = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [patch["patch_id"]]},
    )
    assert preview.status_code == 200
    merge = preview.json()
    history_before = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]

    response = client.post(
        f"/api/projects/demo_project/manuscript/patches/merges/{merge['merge_id']}/confirm",
        json={"decision": "rejected", "reason": "pytest v0.7 merge reject"},
    )

    assert response.status_code == 200
    assert response.json()["merge"]["status"] == "rejected"
    assert response.json()["version"] is None
    history_after = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]
    assert len(history_after) == len(history_before)
