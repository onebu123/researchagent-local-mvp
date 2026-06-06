from __future__ import annotations

import hashlib
import json
import re
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


def _create_patch(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.5 version source"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    assert patch.json()["items"]
    return patch.json()


def test_confirm_patch_creates_version_without_overwriting_draft(demo_project_dir: Path) -> None:
    client = TestClient(app)
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original_hash = _sha256_text(draft_path)
    original_claim_ids = set(re.findall(r"\bclaim_\d{3,}\b", draft_path.read_text(encoding="utf-8")))
    patch = _create_patch(client, demo_project_dir)

    response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest confirm patch"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["patch"]["status"] == "confirmed"
    assert payload["version"] is not None
    version_id = payload["version"]["version_id"]
    assert _sha256_text(draft_path) == original_hash

    version_path = demo_project_dir / "manuscript" / "versions" / f"{version_id}.md"
    assert version_path.exists()
    version_text = version_path.read_text(encoding="utf-8")
    assert "Evidence Checklist" in version_text
    assert original_claim_ids.issubset(set(re.findall(r"\bclaim_\d{3,}\b", version_text)))

    history = _read_json(demo_project_dir / "manuscript" / "versions" / "version_history.json")
    assert any(item["source_patch_id"] == patch["patch_id"] for item in history["versions"])

    versions_response = client.get("/api/projects/demo_project/manuscript/versions")
    version_response = client.get(f"/api/projects/demo_project/manuscript/versions/{version_id}")
    assert versions_response.status_code == 200
    assert any(item["version_id"] == version_id for item in versions_response.json()["versions"])
    assert version_response.status_code == 200
    assert version_response.json()["version"]["version_id"] == version_id
    assert "content" in version_response.json()


def test_rejected_patch_does_not_create_version(demo_project_dir: Path) -> None:
    client = TestClient(app)
    patch = _create_patch(client, demo_project_dir)
    history_before = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]

    response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "rejected", "reason": "pytest reject patch"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["patch"]["status"] == "rejected"
    assert payload["version"] is None
    history_after = client.get("/api/projects/demo_project/manuscript/versions").json()["versions"]
    assert len(history_after) == len(history_before)
    assert not any(item.get("source_patch_id") == patch["patch_id"] for item in history_after)
