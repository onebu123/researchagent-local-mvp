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


def test_merge_preview_can_apply_single_safe_patch_without_modifying_draft(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    before_hash = _sha256(draft_path)
    history_before = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]
    patch = _create_patch(client, demo_project_dir, "pytest v0.6 merge safe")

    response = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [patch["patch_id"]]},
    )

    assert response.status_code == 200
    merge = response.json()
    assert merge["can_apply"] is True
    assert merge["summary"]["safe_items"] >= 1
    assert _sha256(draft_path) == before_hash
    history_after = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]
    assert len(history_after) == len(history_before)
    assert (demo_project_dir / "manuscript" / "patches" / "merges" / f"{merge['merge_id']}.json").exists()
    assert (
        demo_project_dir
        / "manuscript"
        / "patches"
        / "merges"
        / f"{merge['merge_id']}.preview.md"
    ).exists()


def test_merge_preview_blocks_conflicting_patches(demo_project_dir: Path) -> None:
    client = TestClient(app)
    first = _create_patch(client, demo_project_dir, "pytest v0.6 merge first")
    second = _create_patch(client, demo_project_dir, "pytest v0.6 merge second")

    response = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [first["patch_id"], second["patch_id"]]},
    )

    assert response.status_code == 200
    merge = response.json()
    assert merge["can_apply"] is False
    assert merge["summary"]["major_conflicts"] >= 1
    assert merge["conflict_report_file"].startswith("manuscript/patches/conflict_report_")

