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


def _create_patch(client: TestClient, project_dir: Path) -> dict:
    issue = _issue_with_safe_diff(project_dir)
    decision = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "pytest v0.6 patch item edit"},
    )
    assert decision.status_code == 200
    patch = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert patch.status_code == 200
    assert patch.json()["items"]
    return patch.json()


def test_patch_item_edit_records_history_and_reruns_safety(demo_project_dir: Path) -> None:
    client = TestClient(app)
    patch = _create_patch(client, demo_project_dir)
    item = patch["items"][0]
    new_after = item["after"].replace("before submission", "before final submission")
    immutable = {
        key: item.get(key)
        for key in [
            "before",
            "issue_id",
            "decision_id",
            "related_claim_id",
            "section",
            "paragraph_index",
            "sentence_index",
        ]
    }

    response = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/items/{item['patch_item_id']}",
        json={"after": new_after, "reason": "pytest manual wording refinement"},
    )

    assert response.status_code == 200
    updated_item = response.json()["items"][0]
    assert updated_item["after"] == new_after
    assert {key: updated_item.get(key) for key in immutable} == immutable
    assert updated_item["item_status"] == "safe"
    assert updated_item["latest_safety_result"]["safe"] is True
    assert updated_item["manual_edits"]
    assert updated_item["manual_edits"][-1]["old_after"] == item["after"]
    assert updated_item["manual_edits"][-1]["new_after"] == new_after
    assert updated_item["manual_edits"][-1]["reason"] == "pytest manual wording refinement"

    safety_response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/items/{item['patch_item_id']}/safety-check"
    )
    assert safety_response.status_code == 200
    assert safety_response.json()["safety_result"]["safe"] is True


def test_unsafe_patch_item_edit_is_blocked_and_not_applied(demo_project_dir: Path) -> None:
    client = TestClient(app)
    patch = _create_patch(client, demo_project_dir)
    item = patch["items"][0]
    unsafe_after = f"{item['after']} This significantly improved the result."

    edit_response = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/items/{item['patch_item_id']}",
        json={"after": unsafe_after, "reason": "pytest unsafe wording"},
    )
    assert edit_response.status_code == 200
    blocked_item = edit_response.json()["items"][0]
    assert blocked_item["item_status"] == "blocked"
    assert blocked_item["latest_safety_result"]["safe"] is False
    assert "strong conclusion" in " ".join(blocked_item["latest_safety_result"]["blocked_reasons"])

    confirm_response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "pytest confirm unsafe skip"},
    )
    assert confirm_response.status_code == 200
    version = confirm_response.json()["version"]
    assert version is not None
    assert version["summary"]["applied_items"] == 0
    assert version["summary"]["skipped_items"] >= 1

    version_text = (
        demo_project_dir / "manuscript" / "versions" / f"{version['version_id']}.md"
    ).read_text(encoding="utf-8")
    assert unsafe_after not in version_text

