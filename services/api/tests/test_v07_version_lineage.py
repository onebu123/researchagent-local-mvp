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


def _create_confirmed_merge(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.7 lineage decision"},
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
        json={"decision": "confirmed", "reason": "pytest v0.7 lineage confirm"},
    )
    assert confirm.status_code == 200
    return confirm.json()


def test_version_lineage_api_and_file_include_merge_edges(demo_project_dir: Path) -> None:
    client = TestClient(app)
    confirmed = _create_confirmed_merge(client, demo_project_dir)
    merge_id = confirmed["merge"]["merge_id"]
    version_id = confirmed["version"]["version_id"]

    response = client.get("/api/projects/demo_project/manuscript/versions/lineage")

    assert response.status_code == 200
    lineage = response.json()
    assert (demo_project_dir / "manuscript" / "versions" / "version_lineage.json").exists()
    node_ids = {node["id"] for node in lineage["nodes"]}
    assert merge_id in node_ids
    assert version_id in node_ids
    assert any(
        edge["source"] == merge_id
        and edge["target"] == version_id
        and edge["relation"] == "generated_version"
        for edge in lineage["edges"]
    )
    assert lineage["summary"]["merges"] >= 1
    assert lineage["summary"]["versions"] >= 1
